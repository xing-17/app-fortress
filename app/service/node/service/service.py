from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.servicekind import ServiceKind
from app.internal.model.definition.dataframe import DataframeDefinition
from app.internal.model.definition.group import DefinitionGroup
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.resource._global.sources import GlobalSources
from app.resource.asset import DRAMount
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source._common._source import BaseSource
from app.service._common._service import BaseService
from app.service._common.auth import Principal
from app.service.machine.service.service import MachineService
from app.service.node.dra import (
    DRADataResult,
    DRAError,
    DRALimits,
    DRAPool,
    DRARefreshError,
    DRASession,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
)
from app.setting.service import MachineServiceSetting, NodeServiceSetting


class NodeService(BaseService[NodeServiceSetting]):
    """
    Data node, answers what the node holds and runs queries over it

    Catalog methods are answered by the resources themselves (source, dataset, store) and never
    touch the DRA engine. Only `query` does, through one isolated `DRASession` per caller.

    Sessions are pooled by `DRAPool` up to `setting.dra.max_sessions`, see there for the eviction
    rules. When every session is busy a new caller gets `DRABusyError`.

    The node owns a `MachineService` (the state of the host machine over time): it starts and
    stops with the node.

    The DRA views are named "<source>.<dataset>"; catalog methods take `source` and `dataset` apart.

    Args:
    ----------
        setting (NodeServiceSetting):
            Node service setting
        machine (MachineService | None):
            Machine service the node reports from, defaults to one on the default machine setting

    Methods:
    ----------
        list_sources() -> list[dict]:
            Sources with their dataset names
        get_source(source) -> dict:
            One source with its dataset names
        list_datasets(source=None) -> list[dict]:
            Datasets of one source or all
        get_dataset(source, dataset) -> dict:
            One dataset
        list_assetfiles(source, dataset, since=None, until=None) -> list[dict]:
            Assetfiles of a dataset
        list_metadatas(source, dataset, since=None, until=None) -> list[dict]:
            Each assetfile with its metadata, None when it has none
        list_qualities(source, dataset, since=None, until=None) -> list[dict]:
            Each assetfile with its quality, None when it has no metadata
        list_definitions(source, dataset, since=None, until=None) -> list[dict]:
            Definitions grouped by fingerprint with the partitions that carry each of them,
            assetfiles without metadata are skipped
        query(caller, sql) -> DRADataResult:
            Run one SELECT in the caller's DRA session, created on first use
        list_machine_snapshots(hours=None) -> list[dict]:
            Snapshots of the host machine (cpu, memory, disk, network), oldest first
        reset_sessions() -> None:
            Close all idle sessions and retire the busy ones, the next query builds a new one

    """

    kind = ServiceKind.NODE

    def __init__(
        self,
        setting: NodeServiceSetting,
        machine: MachineService | None = None,
    ) -> None:
        super().__init__(setting)
        if machine is None:
            machine = MachineService(MachineServiceSetting())
        self._machine: MachineService = machine
        _dra_max_sessions: int = setting.dra.max_sessions
        _dra_max_idle_seconds: int = setting.dra.max_session_idle_seconds
        self._pool = DRAPool(
            factory=self._build_session,
            max_sessions=_dra_max_sessions,
            max_idle_seconds=_dra_max_idle_seconds,
            on_close=self._log_session_closed,
        )

    def _require_running(self) -> None:
        if not self.is_running:
            raise RuntimeError(f"{self.kind} is not running, state is {self.state}")

    def _start(self) -> None:
        # Load the sources now so a broken setting fails the start
        GlobalSources.list_sources()
        self._machine.start()

    def _stop(self) -> None:
        try:
            self.reset_sessions()
        finally:
            self._machine.stop()

    def health(self) -> dict:
        _res: dict = super().health()
        _stats: dict = self._pool.stats()
        _res.update(_stats)
        return _res

    def _resolve_source(
        self,
        source: str,
    ) -> BaseSource:
        _source: BaseSource | None = GlobalSources.get_source(source, strict=False)
        if _source is None:
            _msg: str = f"Source '{source}' not found on this node"
            raise NodeSourceNotFoundError(_msg)
        return _source

    def _resolve_dataset(
        self,
        source: BaseSource,
        dataset: str,
    ) -> BaseDataset:
        if dataset not in source.list_dataset_names():
            _msg: str = f"Dataset '{source.name}.{dataset}' not found on this node"
            raise NodeDatasetNotFoundError(_msg)
        return source.dataset(dataset)

    def _resolve(
        self,
        source: str,
        dataset: str,
    ) -> BaseDataset:
        _source: BaseSource = self._resolve_source(source)
        return self._resolve_dataset(_source, dataset)

    # --------------------------------------------------
    # Catalog
    # --------------------------------------------------

    # Source Info
    def _retrieve_source_info(
        self,
        source: BaseSource,
    ) -> dict[str, Any]:
        # Only write required attributes
        # Add more attributes as needed
        return {
            "name": source.name,
            "provider": str(source.provider),
            "type": str(source.type),
            "board": str(source.board),
            "country": str(source.country),
            "description": source.description,
            "datasets": source.list_dataset_names(),
        }

    def list_sources(self) -> list[dict[str, Any]]:
        self._require_running()
        _res: list[dict[str, Any]] = []
        for _source in GlobalSources.list_sources():
            _source_info: dict[str, Any] = self._retrieve_source_info(_source)
            _res.append(_source_info)
        return _res

    def get_source(
        self,
        source: str,
    ) -> dict[str, Any]:
        self._require_running()
        _source: BaseSource = self._resolve_source(source)
        return self._retrieve_source_info(_source)

    # Dataset Info
    def _retrieve_dataset_info(
        self,
        source: str,
        dataset: BaseDataset,
    ) -> dict[str, Any]:
        # Only write required attributes
        # Add more attributes as needed
        return {
            "source": source,
            "dataset": f"{source}.{dataset.name}",
            "name": dataset.name,
            "provider": str(dataset.provider),
            "partitions": dataset.partitions,
            "filekind": str(dataset.filekind),
            "frequency": str(dataset.frequency),
            "description": dataset.description,
        }

    def list_datasets(
        self,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require_running()
        if source is None:
            _sources: list[BaseSource] = GlobalSources.list_sources()
        else:
            _source: BaseSource = self._resolve_source(source)
            _sources: list[BaseSource] = [_source]

        _res: list[dict[str, Any]] = []
        for _source in _sources:
            _source_name: str = _source.name
            for _dataset in _source.list_datasets():
                _dataset_info: dict[str, Any] = self._retrieve_dataset_info(
                    source=_source_name,
                    dataset=_dataset,
                )
                _res.append(_dataset_info)
        return _res

    def get_dataset(
        self,
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        self._require_running()
        _source: BaseSource = self._resolve_source(source)
        _dataset: BaseDataset = self._resolve_dataset(_source, dataset)
        return self._retrieve_dataset_info(_source.name, _dataset)

    # Assetfile Info

    def _retrieve_assetfile_info(
        self,
        assetfile: BaseAssetfile,
    ) -> dict[str, Any]:
        return {
            "name": assetfile.name,
            "filekind": str(assetfile.filekind),
            "partitions": dict(assetfile.partitions),
            "size": assetfile.size,
            "modified_at": assetfile.modified_at,
        }

    def list_assetfiles(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        self._require_running()
        _dataset: BaseDataset = self._resolve(source, dataset)
        _res: list[dict[str, Any]] = []
        for _file in _dataset.list_assetfiles(since=since, until=until):
            _assetfile_info: dict[str, Any] = self._retrieve_assetfile_info(_file)
            _res.append(_assetfile_info)
        return _res

    # Partition Info

    def _retrieve_metadata(
        self,
        metadata: AssetfileMetadata,
    ) -> dict[str, Any]:
        # Metadata got nothing to hold back
        # Return all metadata as is
        _res: dict[str, Any] = metadata.export()
        return _res

    def list_metadatas(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, dict[str, Any] | None]]:
        self._require_running()
        _dataset: BaseDataset = self._resolve(source, dataset)
        _res: list[dict[str, Any]] = []
        for _file in _dataset.list_assetfiles(since=since, until=until):
            _file_info: dict[str, Any] = self._retrieve_assetfile_info(_file)
            _metadata: AssetfileMetadata | None = _dataset.read_metadata(_file)
            if _metadata is None:
                _metadata_info = None
            else:
                _metadata_info: dict[str, Any] | None = self._retrieve_metadata(_metadata)

            # Each item protocol follows fixed structure
            _item: dict[str, dict[str, Any] | None] = {
                "assetfile": _file_info,
                "metadata": _metadata_info,
            }
            _res.append(_item)
        return _res

    def list_qualities(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        self._require_running()
        _dataset: BaseDataset = self._resolve(source, dataset)
        _res: list[dict[str, Any]] = []
        for _file in _dataset.list_assetfiles(since=since, until=until):
            _file_info: dict[str, Any] = self._retrieve_assetfile_info(_file)
            _metadata: AssetfileMetadata | None = _dataset.read_metadata(_file)
            if _metadata is None:
                _quality = None
            else:
                _quality: dict[str, Any] | None = _metadata.quality.export()

            # Each item protocol follows fixed structure
            _item: dict[str, dict[str, Any] | None] = {
                "assetfile": _file_info,
                "quality": _quality,
            }
            _res.append(_item)
        return _res

    def list_definitions(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        # Convert definitions to DefinitionGroup objects and group by fingerprint
        # Reduce duplicate partitions for each definition group
        self._require_running()
        _dataset: BaseDataset = self._resolve(source, dataset)
        _groups: dict[str, DefinitionGroup] = {}
        _seen: dict[str, set[tuple[tuple[str, str], ...]]] = {}
        for _file in _dataset.list_assetfiles(since=since, until=until):
            _metadata: AssetfileMetadata | None = _dataset.read_metadata(_file)
            if _metadata is None:
                continue
            _definition: DataframeDefinition = _metadata.definition
            _fp: str | None = _definition.fingerprint
            if _fp is None:
                continue
            if _fp not in _groups:
                _groups[_fp] = DefinitionGroup(
                    fingerprint=_fp,
                    columns=_definition.columns,
                )
                _seen[_fp] = set()
            _key = tuple(sorted(_file.partitions.items()))
            if _key in _seen[_fp]:
                continue
            _seen[_fp].add(_key)
            _groups[_fp].partitions.append(dict(_file.partitions))

        return [_group.export() for _group in _groups.values()]

    # --------------------------------------------------
    # Machine
    # --------------------------------------------------

    def list_machine_snapshots(
        self,
        hours: float | None = None,
    ) -> list[dict[str, Any]]:
        self._require_running()
        # `not > 0` also rejects NaN
        if hours is not None and not hours > 0:
            raise NodeBadRequestError("'hours' must be greater than 0")
        return self._machine.list_snapshots(hours)

    # --------------------------------------------------
    # DRA
    # --------------------------------------------------

    def query(
        self,
        caller: Principal,
        sql: str,
    ) -> DRADataResult:
        self._require_running()
        _meta: dict[str, Any] = {
            "caller": caller.name,
            "sql": sql[:500],  # Log only the first 500 characters of the SQL query
        }
        try:
            with self._pool.lease(caller.name) as _session:
                self._refresh_session(_session)
                _res: DRADataResult = _session.query(sql)
        except DRAError as e:
            _meta["error"] = type(e).__name__
            self.log.warning(
                f"query failed: {caller.name}",
                metadata=_meta,
            )
            raise

        self.log.info(
            f"query ok: {caller.name}",
            metadata=_meta,
            metrics={
                "rows": len(_res.rows),
                "elapsed_ms": _res.elapsed_ms,
            },
        )
        return _res

    def reset_sessions(self) -> None:
        self._pool.reset()

    def _refresh_session(
        self,
        session: DRASession,
    ) -> None:
        _interval: float = self.setting.dra.refresh_interval_seconds
        if not session.has_secrets:
            # Session has no secrets, nothing to refresh
            return

        if time.monotonic() - session.refreshed_at < _interval:
            # Session was refreshed recently, no need to refresh again
            return

        try:
            _mounts: dict[str, DRAMount] = {}
            for _name in session.names:
                _source, _, _dataset = _name.partition(".")
                _dataset_object: BaseDataset = self._resolve(_source, _dataset)
                _mounts[_name] = _dataset_object.asset.get_dra_mount()
            session.refresh(_mounts)
        except DRAError:
            raise
        except Exception as e:
            # What the credential provider says may hold secrets, only the type goes on
            _msg: str = f"cannot refresh credentials: {type(e).__name__}"
            raise DRARefreshError(_msg) from None

    def _build_session(self) -> DRASession:
        _dra_export: dict[str, Any] = self.setting.dra.export()
        _limits = DRALimits.model_validate(_dra_export)
        _mounts: dict[str, DRAMount] = self._mounts()
        _session = DRASession(
            mounts=_mounts,
            limits=_limits,
        )
        self.log.info(
            "DRA session built",
            metadata={
                "limits": _limits.export(),
                "mounts": len(_mounts),
            },
        )
        return _session

    def _log_session_closed(
        self,
        caller: str,
        reason: str,
    ) -> None:
        self.log.info(
            f"session closed: {caller}",
            metadata={
                "caller": caller,
                "reason": reason,
            },
        )

    def _mounts(self) -> dict[str, DRAMount]:
        _res: dict[str, DRAMount] = {}
        for _source in GlobalSources.list_sources():
            for _dataset in _source.list_datasets():
                if _dataset.filekind != AssetFileKind.PARQUET:
                    continue
                # A view over no files cannot be created
                if not _dataset.asset.list_assetfiles():
                    continue
                _identifier: str = f"{_source.name}.{_dataset.name}"
                _res[_identifier] = _dataset.asset.get_dra_mount()
        return _res
