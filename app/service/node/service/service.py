from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.servicekind import ServiceKind
from app.internal.model.definition.dataframe import DataframeDefinition
from app.internal.model.definition.group import DefinitionGroup
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.resource._global.sources import GlobalSources
from app.resource.asset import DRAMount
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source._common._run import DatasetRun
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
    NodeBusyError,
    NodeDatasetNotFoundError,
    NodeRunNotFoundError,
    NodeSourceNotFoundError,
)
from app.setting.service import MachineServiceSetting, NodeServiceSetting

# A failure message may carry paths or URLs, only its head leaves the node
_MAX_RUN_ERROR_CHARS = 500


class NodeService(BaseService[NodeServiceSetting]):
    """
    Data node, answers what the node holds and runs queries over it

    Catalog methods are answered by the resources themselves (source, dataset, store) and never
    touch the DRA engine. Only `query` does, through one isolated `DRASession` per caller.

    Sessions are pooled by `DRAPool` up to `setting.dra.max_sessions`, see there for the eviction
    rules. When every session is busy a new caller gets `DRABusyError`.

    The node owns a `MachineService` (the state of the host machine over time): it starts and
    stops with the node.

    Dataset runs are started in the background, `submit_dataset_run` returns the run record at once.
    A source runs at most `source.max_threads` datasets at a time, the node runs at most
    `setting.max_threads` sources at a time, and a dataset never runs twice at the same time.
    A submit over any of these limits is refused with `NodeBusyError`, nothing is queued.
    On start the node fails the STARTED runs it left behind (see `node`), on stop it waits for the
    runs in flight.

    The DRA views are named "<source>.<dataset>"; catalog methods take `source` and `dataset` apart.

    Args:
    ----------
        setting (NodeServiceSetting):
            Node service setting
        machine (MachineService | None):
            Machine service the node reports from, defaults to one on the default machine setting
        node (str):
            Node name, stamped on the runs it starts as their owner. Keep it stable across restarts,
            it is how the node finds its own interrupted runs, default is "centre"

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
        list_runs(source, dataset, status=None, limit=None) -> list[dict]:
            Run records of a dataset, newest first, optionally of one status and capped at limit
        submit_dataset_run(source, dataset, params=None) -> dict:
            Start a run of a dataset in the background, returns its STARTED record
        get_dataset_run(source, dataset, id) -> dict:
            Record of one run, poll it until its status is completed or failed
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
        node: str = "centre",
    ) -> None:
        super().__init__(setting)
        if machine is None:
            machine = MachineService(MachineServiceSetting())
        self._machine: MachineService = machine
        self._node: str = node

        # Runs in flight, as (source, dataset)
        # one pool per source, both guarded by the lock
        self._run_lock = threading.Lock()
        self._active: set[tuple[str, str]] = set()
        self._run_pools: dict[str, ThreadPoolExecutor] = {}

        # DRA session pool for this node
        # used to query ALL datasets
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
            _msg: str = f"{self.kind} is not running, state is {self.state}"
            raise RuntimeError(_msg)

    def _start(self) -> None:
        # Load the sources now so a broken setting fails the start
        _sources: list[BaseSource] = GlobalSources.list_sources()
        self._recover_runs(_sources)
        self._machine.start()

    def _stop(self) -> None:
        try:
            # Runs in flight are waited for
            # a new submit is refused since the node is not running
            self._wait_runs()
        finally:
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
        _source: BaseSource | None = GlobalSources.get_source(
            name=source,
            strict=False,
        )
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

    # Run Info

    def _retrieve_run_info(
        self,
        run: DatasetRun,
    ) -> dict[str, Any]:
        # Assetfile URIs are not exposed (same as `_retrieve_assetfile_info`), only how many
        _error: str | None = run.error
        if _error is not None:
            _error = _error[:_MAX_RUN_ERROR_CHARS]
        return {
            "id": run.id,
            "status": str(run.status),
            "params": run.params,
            "assetfile_count": len(run.assetfiles),
            "height": run.height,
            "width": run.width,
            "error": _error,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "duration": run.duration,
        }

    def list_runs(
        self,
        source: str,
        dataset: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self._require_running()
        _statuses: list[str] = [str(_s) for _s in ComputeStatus]
        if status is not None and status not in _statuses:
            raise NodeBadRequestError(f"'status' must be one of {_statuses}")
        if limit is not None and limit < 1:
            raise NodeBadRequestError("'limit' must be at least 1")

        _dataset: BaseDataset = self._resolve(source, dataset)
        _runs: list[DatasetRun] = _dataset.list_runs(
            status=status,
            limit=limit,
        )
        return [self._retrieve_run_info(_run) for _run in _runs]

    def get_dataset_run(
        self,
        source: str,
        dataset: str,
        id: str,
    ) -> dict[str, Any]:
        self._require_running()
        _dataset: BaseDataset = self._resolve(source, dataset)
        _run: DatasetRun | None = _dataset.get_run(id)
        if _run is None:
            _msg: str = f"Run '{id}' not found on '{source}.{dataset}'"
            raise NodeRunNotFoundError(_msg)
        return self._retrieve_run_info(_run)

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def submit_dataset_run(
        self,
        source: str,
        dataset: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_running()
        if params is not None and not isinstance(params, dict):
            raise NodeBadRequestError("'params' must be a JSON object")

        _source: BaseSource = self._resolve_source(source)
        _dataset: BaseDataset = self._resolve_dataset(_source, dataset)
        _key: tuple[str, str] = (_source.name, _dataset.name)
        self._reserve(_source, _key)

        _run: DatasetRun | None = None
        try:
            # The record is written before the thread starts, so the id is pollable at once
            _run = _dataset.start_run(
                params=params,
                owner=self._node,
            )
            self._pool_of(_source).submit(
                self._execute,
                _dataset,
                _run,
                params,
                _key,
            )
        except BaseException as e:
            if _run is not None:
                self._fail_quietly(_dataset, _run, e)
            self._release(_key)
            raise
        return self._retrieve_run_info(_run)

    def _reserve(
        self,
        source: BaseSource,
        key: tuple[str, str],
    ) -> None:
        with self._run_lock:
            # Do not allow the same dataset to run concurrently
            if key in self._active:
                _msg: str = f"Dataset '{key[0]}.{key[1]}' is already running"
                raise NodeBusyError(_msg)

            # Check if the source has reached its maximum number of concurrent runs
            # Gather all currently running sources
            _running: set[str] = set()
            for _s, _ in self._active:
                _running.add(_s)
            _of_source: int = sum(1 for _s, _ in self._active if _s == source.name)
            if _of_source >= source.max_threads:
                _msg: str = f"Source '{source.name}' is at its limit of {source.max_threads} running dataset(s)"
                raise NodeBusyError(_msg)

            # Check if the node has reached its maximum number of concurrent sources
            _max_threads: int = self.setting.max_threads
            if source.name not in _running and len(_running) >= _max_threads:
                _msg: str = f"Node is at its limit of {_max_threads} running source(s)"
                raise NodeBusyError(_msg)
            self._active.add(key)

    def _release(
        self,
        key: tuple[str, str],
    ) -> None:
        with self._run_lock:
            self._active.discard(key)

    def _pool_of(
        self,
        source: BaseSource,
    ) -> ThreadPoolExecutor:
        with self._run_lock:
            _pool: ThreadPoolExecutor | None = self._run_pools.get(source.name)
            if _pool is None:
                _pool = ThreadPoolExecutor(
                    max_workers=source.max_threads,
                    thread_name_prefix=f"run-{source.name}",
                )
                self._run_pools[source.name] = _pool
            return _pool

    def _execute(
        self,
        dataset: BaseDataset,
        run: DatasetRun,
        params: dict[str, Any] | None,
        key: tuple[str, str],
    ) -> None:
        try:
            dataset.run(params=params, run=run)
        except Exception as e:
            # A failed step is already recorded
            # logged by `run`, only a failure outside the steps lands here
            if not run.is_finished:
                self._fail_quietly(dataset, run, e)
        finally:
            self._release(key)

    def _fail_quietly(
        self,
        dataset: BaseDataset,
        run: DatasetRun,
        error: BaseException,
    ) -> None:
        _meta: dict[str, Any] = {
            "dataset": dataset.name,
            "run": run.id,
            "error": type(error).__name__,
        }
        try:
            dataset.fail_run(run, str(error))
        except Exception as e:
            # The record stays STARTED until the next start of the node recovers it
            _meta["record_error"] = type(e).__name__
        self.log.warning(f"dataset run failed: {dataset.name}", metadata=_meta)

    def _wait_runs(self) -> None:
        with self._run_lock:
            _pools: list[ThreadPoolExecutor] = list(self._run_pools.values())
            self._run_pools.clear()
        for _pool in _pools:
            _pool.shutdown(wait=True)

    def _recover_runs(
        self,
        sources: list[BaseSource],
    ) -> None:
        # Fail the runs a previous process of this node left STARTED, nothing of ours is running yet
        for _source in sources:
            for _dataset in _source.list_datasets():
                _name: str = f"{_source.name}.{_dataset.name}"
                try:
                    _recovered: list[DatasetRun] = _dataset.recover_runs(owner=self._node)
                except Exception as e:
                    # One unreadable store must not keep the node from starting
                    self.log.warning(
                        f"cannot recover runs: {_name}",
                        metadata={
                            "dataset": _name,
                            "error": type(e).__name__,
                        },
                    )
                    continue
                if _recovered:
                    self.log.warning(
                        f"recovered {len(_recovered)} interrupted run(s): {_name}",
                        metadata={"dataset": _name, "runs": [_r.id for _r in _recovered]},
                    )

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
