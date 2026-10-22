from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.servicekind import ServiceKind
from app.internal.model.definition.dataframe import DataframeDefinition
from app.internal.model.definition.group import DefinitionGroup
from app.internal.model.dra import DRADataResult, DRAError, DRAMount
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.resource._global.sources import GlobalSources
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source._common._source import BaseSource
from app.service._common._service import BaseService
from app.service.node.dra import DRALimits, DRASession
from app.service.node.service.auth import Principal
from app.service.node.service.errors import (
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
)
from app.setting.service import NodeServiceSetting

_SQL_LOG_CHARS = 500


class NodeService(BaseService[NodeServiceSetting]):
    """
    Data node, answers what the node holds and runs queries over it

    Catalog methods are answered by the resources themselves (source, dataset, store) and never
    touch the DRA engine. Only `query` does, through one isolated `DRASession` per caller.

    The DRA views are named "<source>.<dataset>"; catalog methods take `source` and `dataset` apart.

    Args:
    ----------
        setting (NodeServiceSetting):
            Node service setting

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
        reset_sessions() -> None:
            Close all sessions, the next query builds a new one

    """

    kind = ServiceKind.NODE

    def __init__(
        self,
        setting: NodeServiceSetting,
    ) -> None:
        super().__init__(setting)
        self._sessions: dict[str, DRASession] = {}
        self._session_lock = threading.Lock()

    def _require_running(self) -> None:
        if not self.is_running:
            raise RuntimeError(f"{self.kind} is not running, state is {self.state}")

    def _start(self) -> None:
        # Load the sources now so a broken setting fails the start, not the first request
        GlobalSources.list_sources()

    def _stop(self) -> None:
        self.reset_sessions()

    def health(self) -> dict:
        _res: dict = super().health()
        _res["sessions"] = len(self._sessions)
        return _res

    def _resolve_source(
        self,
        source: str,
    ) -> BaseSource:
        _source: BaseSource | None = GlobalSources.get_source(source, strict=False)
        if _source is None:
            raise NodeSourceNotFoundError(f"Source '{source}' not found on this node")
        return _source

    def _resolve_dataset(
        self,
        source: BaseSource,
        dataset: str,
    ) -> BaseDataset:
        if dataset not in source.list_dataset_names():
            raise NodeDatasetNotFoundError(f"Dataset '{source.name}.{dataset}' not found on this node")
        return source.dataset(dataset)

    def _resolve(
        self,
        source: str,
        dataset: str,
    ) -> BaseDataset:
        return self._resolve_dataset(self._resolve_source(source), dataset)

    # --------------------------------------------------
    # Catalog
    # --------------------------------------------------

    # Source Info
    def _retrieve_source_info(
        self,
        source: BaseSource,
    ) -> dict[str, Any]:
        return {
            "name": source.name,
            "provider": source.provider,
            "type": source.type,
            "board": source.board,
            "country": source.country,
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
        return {
            "source": source,
            "dataset": f"{source}.{dataset.name}",
            "name": dataset.name,
            "provider": dataset.provider,
            "partitions": dataset.partitions,
            "filekind": dataset.filekind,
            "frequency": dataset.frequency,
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
            "filekind": assetfile.filekind,
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
    # DRA
    # --------------------------------------------------

    def query(
        self,
        caller: Principal,
        sql: str,
    ) -> DRADataResult:
        self._require_running()
        _session: DRASession = self._session_of(caller)
        _meta: dict[str, Any] = {
            "caller": caller.name,
            "sql": sql[:_SQL_LOG_CHARS],
        }
        try:
            _res: DRADataResult = _session.query(sql)
        except DRAError as e:
            _meta["error"] = type(e).__name__
            self.log.warning(f"query failed: {caller.name}", metadata=_meta)
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
        with self._session_lock:
            _sessions: list[DRASession] = list(self._sessions.values())
            self._sessions.clear()
        for _session in _sessions:
            _session.close()

    def _session_of(
        self,
        caller: Principal,
    ) -> DRASession:
        # Built under the lock, so one caller never ends up with two sessions
        with self._session_lock:
            _session: DRASession | None = self._sessions.get(caller.name)
            if _session is None:
                _dra_setting = self.setting.dra.export()
                _limits = DRALimits.model_validate(_dra_setting)
                _session = DRASession(
                    mounts=self._mounts(),
                    limits=_limits,
                )
                self._sessions[caller.name] = _session
            return _session

    def _mounts(self) -> dict[str, DRAMount]:
        _res: dict[str, DRAMount] = {}
        for _source in GlobalSources.list_sources():
            for _dataset in _source.list_datasets():
                if _dataset.filekind != AssetFileKind.PARQUET:
                    continue
                # A view over no files cannot be created
                if not _dataset.asset.list_assetfiles():
                    continue
                _res[f"{_source.name}.{_dataset.name}"] = _dataset.asset.get_dra_mount()
        return _res
