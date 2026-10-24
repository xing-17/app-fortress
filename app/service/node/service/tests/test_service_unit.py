from __future__ import annotations

import io
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from app.internal.constant.servicestate import ServiceState
from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.sources import GlobalSources
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common._run import DatasetRun
from app.resource.source._common.tests.fakes.base import FakeDataset, FakeSource
from app.resource.store.file.store import FileStore
from app.service._common.auth import Principal
from app.service.machine.service.service import MachineService
from app.service.node.dra import DRABusyError, DRADataResult, DRARefreshError, DRARejectedError, DRASession
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeBusyError,
    NodeDatasetNotFoundError,
    NodeRunNotFoundError,
    NodeSourceNotFoundError,
)
from app.service.node.service.service import NodeService
from app.setting.service import MachineServiceSetting, NodeServiceSetting


@pytest.fixture(autouse=True)
def _reset_globals():
    GlobalIdentities.reset()
    GlobalSources.reset()
    yield
    GlobalSources.reset()
    GlobalIdentities.reset()


@pytest.fixture
def log(monkeypatch):
    _log = MagicMock(spec=LogStream)
    monkeypatch.setattr(GlobalLogStreams, "resolve", lambda value, default: _log)
    return _log


@pytest.fixture
def source(tmp_path):
    _source = FakeSource(
        name="src",
        vault=LocalVault(name="v", path=tmp_path / "vault"),
        store=FileStore(name="s", path=str(tmp_path / "store")),
        log_stream=LogStream(name="src", console_verbose=False),
    )
    GlobalSources.sources = {"src": _source}
    return _source


@pytest.fixture
def service(log, source):
    _service = NodeService(NodeServiceSetting())
    _service.start()
    yield _service
    _service.stop()


def _write(source, dataset_name, name, df, partitions=None, metadata=True):
    _dataset = source.dataset(dataset_name)
    _file = _dataset.asset.assetfile(name, partitions=partitions)
    _buffer = io.BytesIO()
    df.write_parquet(_buffer)
    _dataset.write_assetfile(_file, _buffer.getvalue())
    if metadata:
        _dataset.write_metadata(_file, _dataset.get_metadata(df))
    return _file


_ALICE = Principal(name="alice")
_BOB = Principal(name="bob")


class TestLifecycle:
    def test_methods_require_a_running_service(self, log, source):
        _service = NodeService(NodeServiceSetting())
        with pytest.raises(RuntimeError, match="not running"):
            _service.list_sources()
        with pytest.raises(RuntimeError, match="not running"):
            _service.query(_ALICE, "SELECT 1")

    def test_health_reports_sessions(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        assert service.health()["sessions"] == 0
        service.query(_ALICE, "SELECT * FROM src.alpha")
        assert service.health()["sessions"] == 1

    def test_stop_closes_sessions(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        service.stop()
        assert service.health()["sessions"] == 0


class TestCatalog:
    def test_list_sources(self, service):
        _res = service.list_sources()
        assert [s["name"] for s in _res] == ["src"]
        assert sorted(_res[0]["datasets"]) == ["alpha", "beta"]

    def test_list_sources_hides_paths_and_log_wiring(self, service):
        _res = service.list_sources()[0]
        assert "provision_path" not in _res
        assert "log_stream" not in _res
        assert "vault" not in _res
        assert "store" not in _res

    def test_get_source(self, service):
        assert service.get_source("src")["name"] == "src"

    def test_get_unknown_source_raises(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.get_source("nope")

    def test_list_datasets_of_all_sources(self, service):
        _res = service.list_datasets()
        assert sorted(d["dataset"] for d in _res) == ["src.alpha", "src.beta"]

    def test_list_datasets_of_one_source(self, service):
        _res = service.list_datasets(source="src")
        assert sorted(d["name"] for d in _res) == ["alpha", "beta"]

    def test_list_datasets_of_unknown_source_raises(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.list_datasets(source="nope")

    def test_get_dataset(self, service):
        _res = service.get_dataset("src", "beta")
        assert _res["dataset"] == "src.beta"
        assert _res["source"] == "src"
        assert _res["partitions"] == ["year"]

    def test_get_dataset_unknown_source_raises(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.get_dataset("nope", "alpha")

    @pytest.mark.parametrize("name", ["nope", "src.alpha", ""])
    def test_get_dataset_unknown_dataset_raises(self, service, name):
        with pytest.raises(NodeDatasetNotFoundError):
            service.get_dataset("src", name)


class TestAssetfiles:
    def test_lists_assetfiles_with_partitions(self, service, source):
        _write(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        _write(source, "beta", "b.parquet", pl.DataFrame({"a": [1]}), {"year": "2024"})
        _res = service.list_assetfiles("src", "beta")
        assert sorted(p["partitions"]["year"] for p in _res) == ["2023", "2024"]

    def test_does_not_expose_the_uri(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = service.list_assetfiles("src", "alpha")
        assert "uri" not in _res[0]

    def test_empty_dataset(self, service):
        assert service.list_assetfiles("src", "alpha") == []

    def test_unknown_dataset_raises(self, service):
        with pytest.raises(NodeDatasetNotFoundError):
            service.list_assetfiles("src", "nope")


class TestMetadatas:
    def test_pairs_assetfile_with_metadata(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = service.list_metadatas("src", "alpha")
        assert _res[0]["assetfile"]["name"] == "a.parquet"
        assert set(_res[0]["metadata"]) == {"quality", "definition"}

    def test_assetfile_without_metadata_has_none(self, service, source):
        _write(source, "alpha", "bare.parquet", pl.DataFrame({"a": [1]}), metadata=False)
        assert service.list_metadatas("src", "alpha")[0]["metadata"] is None


class TestQualities:
    def test_returns_quality_per_assetfile(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = service.list_qualities("src", "alpha")
        assert len(_res) == 1
        assert _res[0]["assetfile"]["name"] == "a.parquet"
        assert _res[0]["quality"]["height"] == 3

    def test_assetfile_without_metadata_has_no_quality(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _write(source, "alpha", "bare.parquet", pl.DataFrame({"a": [1]}), metadata=False)
        _by_name = {q["assetfile"]["name"]: q["quality"] for q in service.list_qualities("src", "alpha")}
        assert _by_name["a.parquet"] is not None
        assert _by_name["bare.parquet"] is None


class TestDefinitions:
    def test_partitions_are_grouped_by_definition(self, service, source):
        _same = pl.DataFrame({"a": [1]})
        _other = pl.DataFrame({"a": [1], "b": [2]})
        _write(source, "beta", "a.parquet", _same, {"year": "2022"})
        _write(source, "beta", "b.parquet", _same, {"year": "2023"})
        _write(source, "beta", "c.parquet", _other, {"year": "2024"})

        _res = service.list_definitions("src", "beta")
        _by_size = {len(g["columns"]): g for g in _res}
        assert sorted(p["year"] for p in _by_size[1]["partitions"]) == ["2022", "2023"]
        assert [p["year"] for p in _by_size[2]["partitions"]] == ["2024"]

    def test_same_partition_is_listed_once(self, service, source):
        _df = pl.DataFrame({"a": [1]})
        _write(source, "beta", "a.parquet", _df, {"year": "2022"})
        _write(source, "beta", "b.parquet", _df, {"year": "2022"})
        _res = service.list_definitions("src", "beta")
        assert len(_res) == 1
        assert _res[0]["partitions"] == [{"year": "2022"}]

    def test_assetfile_without_metadata_is_skipped(self, service, source):
        _write(source, "beta", "bare.parquet", pl.DataFrame({"a": [1]}), {"year": "2022"}, metadata=False)
        assert service.list_definitions("src", "beta") == []


class TestRuns:
    def test_lists_the_runs_of_a_dataset(self, service, source):
        _dataset = source.dataset("alpha")
        _dataset.run(params={"date": "2024-01-01"})
        _res = service.list_runs("src", "alpha")
        assert len(_res) == 1
        assert _res[0]["status"] == "completed"
        assert _res[0]["params"] == {"date": "2024-01-01"}
        assert _res[0]["assetfile_count"] == 1
        assert _res[0]["height"] == 3
        assert _res[0]["width"] == 2
        assert _res[0]["error"] is None
        assert _res[0]["finished_at"] >= _res[0]["started_at"]

    def test_does_not_expose_the_assetfile_uris(self, service, source):
        source.dataset("alpha").run()
        _res = service.list_runs("src", "alpha")
        assert "assetfiles" not in _res[0]
        assert "provider" not in _res[0]

    def test_dataset_without_runs_is_empty(self, service):
        assert service.list_runs("src", "alpha") == []

    def test_newest_first_and_limit(self, service, source):
        _dataset = source.dataset("alpha")
        for _ in range(3):
            _dataset.run()
        _all = service.list_runs("src", "alpha")
        assert [r["started_at"] for r in _all] == sorted((r["started_at"] for r in _all), reverse=True)
        assert len(service.list_runs("src", "alpha", limit=2)) == 2

    def test_status_filter(self, service, source):
        _dataset = source.dataset("alpha")
        _dataset.run()
        _failed = DatasetRun(provider="tushare", dataset="alpha")
        _failed.fail("boom")
        _dataset._write_run(_failed)
        assert [r["error"] for r in service.list_runs("src", "alpha", status="failed")] == ["boom"]
        assert len(service.list_runs("src", "alpha", status="completed")) == 1
        assert service.list_runs("src", "alpha", status="started") == []

    def test_a_long_error_is_clipped(self, service, source):
        _dataset = source.dataset("alpha")
        _failed = DatasetRun(provider="tushare", dataset="alpha")
        _failed.fail("x" * 5000)
        _dataset._write_run(_failed)
        assert len(service.list_runs("src", "alpha")[0]["error"]) == 500

    @pytest.mark.parametrize("status", ["done", "COMPLETED", ""])
    def test_unknown_status_raises(self, service, status):
        with pytest.raises(NodeBadRequestError, match="status"):
            service.list_runs("src", "alpha", status=status)

    @pytest.mark.parametrize("limit", [0, -1])
    def test_limit_must_be_at_least_one(self, service, limit):
        with pytest.raises(NodeBadRequestError, match="limit"):
            service.list_runs("src", "alpha", limit=limit)

    def test_unknown_source_raises(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.list_runs("nope", "alpha")

    def test_unknown_dataset_raises(self, service):
        with pytest.raises(NodeDatasetNotFoundError):
            service.list_runs("src", "nope")


class TestSubmitDatasetRun:
    @pytest.fixture
    def gate(self, service, monkeypatch):
        # Every dataset run blocks in extract until the gate opens
        _gate = threading.Event()

        def _extract(self, params=None):
            _gate.wait(10)
            return pl.DataFrame({"a": [1]})

        monkeypatch.setattr(FakeDataset, "extract", _extract)
        yield _gate
        _gate.set()

    @staticmethod
    def _wait(service, source, dataset, id):
        for _ in range(200):
            _res = service.get_dataset_run(source, dataset, id)
            if _res["status"] != "started":
                return _res
            time.sleep(0.05)
        raise AssertionError("run did not finish")

    @staticmethod
    def _second_source(tmp_path, name="src2", max_threads=1):
        return FakeSource(
            name=name,
            max_threads=max_threads,
            vault=LocalVault(name="v2", path=tmp_path / "vault2"),
            store=FileStore(name="s2", path=str(tmp_path / "store2")),
            log_stream=LogStream(name=name, console_verbose=False),
        )

    def test_returns_a_started_record_at_once(self, service, gate):
        _res = service.submit_dataset_run("src", "alpha", {"k": "v"})
        assert _res["status"] == "started"
        assert _res["params"] == {"k": "v"}
        assert service.get_dataset_run("src", "alpha", _res["id"])["status"] == "started"

    def test_run_completes_in_the_background(self, service, gate):
        _id = service.submit_dataset_run("src", "alpha")["id"]
        gate.set()
        _done = self._wait(service, "src", "alpha", _id)
        assert _done["status"] == "completed"
        assert _done["assetfile_count"] == 1

    def test_run_is_owned_by_the_node(self, log, source, gate):
        _service = NodeService(NodeServiceSetting(), node="n1")
        _service.start()
        try:
            _id = _service.submit_dataset_run("src", "alpha")["id"]
            assert source.dataset("alpha").get_run(_id).owner == "n1"
        finally:
            gate.set()
            _service.stop()

    def test_a_failed_run_is_reported_failed(self, service, monkeypatch):
        def _boom(self, params=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(FakeDataset, "extract", _boom)
        _id = service.submit_dataset_run("src", "alpha")["id"]
        _done = self._wait(service, "src", "alpha", _id)
        assert (_done["status"], _done["error"]) == ("failed", "boom")

    def test_same_dataset_cannot_run_twice(self, service, gate):
        service.submit_dataset_run("src", "alpha")
        with pytest.raises(NodeBusyError, match="already running"):
            service.submit_dataset_run("src", "alpha")

    def test_dataset_can_run_again_once_finished(self, service, gate):
        _id = service.submit_dataset_run("src", "alpha")["id"]
        gate.set()
        self._wait(service, "src", "alpha", _id)
        # The slot is released after the record is final, give the worker a moment
        for _ in range(100):
            try:
                _second = service.submit_dataset_run("src", "alpha")
                break
            except NodeBusyError:
                time.sleep(0.02)
        else:
            raise AssertionError("slot was not released")
        assert _second["id"] != _id

    def test_source_limit_refuses_another_dataset(self, service, gate):
        service.submit_dataset_run("src", "alpha")
        with pytest.raises(NodeBusyError, match="Source 'src'"):
            service.submit_dataset_run("src", "beta")

    def test_source_limit_follows_max_threads(self, service, tmp_path, gate):
        GlobalSources.sources = {"wide": self._second_source(tmp_path, "wide", max_threads=2)}
        service.submit_dataset_run("wide", "alpha")
        service.submit_dataset_run("wide", "beta")

    def test_node_limit_refuses_another_source(self, log, source, tmp_path, gate):
        GlobalSources.sources = {
            "src": source,
            "src2": self._second_source(tmp_path, "src2"),
            "src3": self._second_source(tmp_path, "src3"),
        }
        _service = NodeService(NodeServiceSetting(max_threads=2))
        _service.start()
        try:
            _service.submit_dataset_run("src", "alpha")
            _service.submit_dataset_run("src2", "alpha")
            with pytest.raises(NodeBusyError, match="Node"):
                _service.submit_dataset_run("src3", "alpha")
        finally:
            gate.set()
            _service.stop()

    def test_a_refused_submit_writes_no_record(self, service, source, gate):
        service.submit_dataset_run("src", "alpha")
        with pytest.raises(NodeBusyError):
            service.submit_dataset_run("src", "beta")
        assert source.dataset("beta").list_runs() == []

    def test_params_must_be_an_object(self, service):
        with pytest.raises(NodeBadRequestError, match="params"):
            service.submit_dataset_run("src", "alpha", ["x"])

    def test_unknown_source_and_dataset_raise(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.submit_dataset_run("nope", "alpha")
        with pytest.raises(NodeDatasetNotFoundError):
            service.submit_dataset_run("src", "nope")

    def test_requires_a_running_service(self, log, source):
        with pytest.raises(RuntimeError, match="not running"):
            NodeService(NodeServiceSetting()).submit_dataset_run("src", "alpha")

    def test_stop_waits_for_the_runs_in_flight(self, log, source, gate):
        _service = NodeService(NodeServiceSetting())
        _service.start()
        _id = _service.submit_dataset_run("src", "alpha")["id"]
        threading.Timer(0.3, gate.set).start()
        _service.stop()
        assert source.dataset("alpha").get_run(_id).status == "completed"


class TestGetDatasetRun:
    def test_returns_the_record(self, service, source):
        _dataset = source.dataset("alpha")
        _dataset.run()
        _id = _dataset.list_runs()[0].id
        _res = service.get_dataset_run("src", "alpha", _id)
        assert (_res["id"], _res["status"]) == (_id, "completed")

    def test_unknown_run_raises(self, service):
        with pytest.raises(NodeRunNotFoundError):
            service.get_dataset_run("src", "alpha", "run-missing")

    def test_unknown_source_and_dataset_raise(self, service):
        with pytest.raises(NodeSourceNotFoundError):
            service.get_dataset_run("nope", "alpha", "x")
        with pytest.raises(NodeDatasetNotFoundError):
            service.get_dataset_run("src", "nope", "x")

    def test_requires_a_running_service(self, log, source):
        with pytest.raises(RuntimeError, match="not running"):
            NodeService(NodeServiceSetting()).get_dataset_run("src", "alpha", "x")


class TestRecoverRunsOnStart:
    def test_fails_the_runs_the_node_left_started(self, log, source):
        _dataset = source.dataset("alpha")
        _run = _dataset.start_run(owner="n1")
        _service = NodeService(NodeServiceSetting(), node="n1")
        _service.start()
        _service.stop()
        assert _dataset.get_run(_run.id).status == "failed"

    def test_keeps_the_runs_of_another_node(self, log, source):
        _dataset = source.dataset("alpha")
        _run = _dataset.start_run(owner="n2")
        _service = NodeService(NodeServiceSetting(), node="n1")
        _service.start()
        _service.stop()
        assert _dataset.get_run(_run.id).status == "started"

    def test_an_unreadable_store_does_not_block_the_start(self, log, source, monkeypatch):
        def _boom(self, owner):
            raise OSError("store down")

        monkeypatch.setattr(FakeDataset, "recover_runs", _boom)
        _service = NodeService(NodeServiceSetting())
        _service.start()
        assert _service.is_running
        _service.stop()


class TestMachine:
    def test_lists_the_recorded_snapshots(self, service):
        service._machine._record()
        _res = service.list_machine_snapshots()
        assert len(_res) == 1
        assert _res[0]["mem_total_mb"] > 0

    def test_hours_narrows_the_window(self, service):
        service._machine._record()
        assert len(service.list_machine_snapshots(hours=1)) == 1

    @pytest.mark.parametrize("hours", [0, -1, float("nan")])
    def test_hours_must_be_above_zero(self, service, hours):
        with pytest.raises(NodeBadRequestError):
            service.list_machine_snapshots(hours=hours)

    def test_requires_a_running_service(self, log, source):
        _service = NodeService(NodeServiceSetting())
        with pytest.raises(RuntimeError, match="not running"):
            _service.list_machine_snapshots()

    def test_machine_follows_the_node_lifecycle(self, log, source):
        _service = NodeService(NodeServiceSetting())
        assert _service._machine.state == ServiceState.CREATED
        _service.start()
        assert _service._machine.is_running
        _service.stop()
        assert _service._machine.state == ServiceState.STOPPED

    def test_uses_the_given_machine_service(self, log, source):
        _machine = MachineService(MachineServiceSetting(interval_seconds=30))
        _service = NodeService(NodeServiceSetting(), machine=_machine)
        assert _service._machine is _machine


class TestQuery:
    def test_runs_a_select(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = service.query(_ALICE, "SELECT sum(a) AS total FROM src.alpha")
        assert _res.rows == [[6]]

    def test_partition_column_is_queryable(self, service, source):
        _write(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        _res = service.query(_ALICE, "SELECT year FROM src.beta")
        assert _res.rows == [["2023"]]

    def test_a_caller_keeps_one_session(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        _first = service._pool.session("alice")
        service.query(_ALICE, "SELECT * FROM src.alpha")
        assert service._pool.session("alice") is _first

    def test_callers_get_isolated_sessions(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        service.query(_BOB, "SELECT * FROM src.alpha")
        assert service._pool.session("alice") is not service._pool.session("bob")

    def test_empty_dataset_is_not_mounted(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        with pytest.raises(Exception, match="beta"):
            service.query(_ALICE, "SELECT * FROM src.beta")

    def test_no_mountable_dataset_is_rejected(self, service):
        with pytest.raises(DRARejectedError, match="at least one mount"):
            service.query(_ALICE, "SELECT 1")

    def test_non_select_is_rejected_and_logged(self, service, source, log):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        with pytest.raises(DRARejectedError):
            service.query(_ALICE, "DROP TABLE x")
        assert log.warning.call_args.kwargs["metadata"]["caller"] == "alice"

    def test_success_is_logged_with_the_caller(self, service, source, log):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        _call = log.info.call_args_list[-1]
        assert _call.kwargs["metadata"]["caller"] == "alice"
        assert _call.kwargs["metrics"]["rows"] == 1

    def test_reset_sessions_builds_a_new_one(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        _first = service._pool.session("alice")
        service.reset_sessions()
        service.query(_ALICE, "SELECT * FROM src.alpha")
        assert service._pool.session("alice") is not _first

    def test_limits_come_from_the_setting(self, log, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": list(range(50))}))
        _service = NodeService(NodeServiceSetting(dra={"max_rows": 5}))
        _service.start()
        try:
            _res = _service.query(_ALICE, "SELECT * FROM src.alpha")
        finally:
            _service.stop()
        assert len(_res.rows) == 5
        assert _res.truncated_by == "rows"


_SQL = "SELECT * FROM src.alpha"


class TestQueryRefresh:
    @staticmethod
    def _fake_session(refreshed_at: float = 0.0) -> MagicMock:
        _session = MagicMock(
            names=["src.alpha"],
            has_secrets=True,
            refreshed_at=refreshed_at,
        )
        _session.query.return_value = DRADataResult(
            columns=["a"],
            types=["BIGINT"],
            rows=[[1]],
            truncated=False,
            truncated_by=None,
            elapsed_ms=0.0,
        )
        return _session

    @staticmethod
    def _serve(monkeypatch, session, **dra) -> NodeService:
        monkeypatch.setattr(NodeService, "_build_session", lambda self: session)
        _service = NodeService(NodeServiceSetting(dra=dra))
        _service.start()
        monkeypatch.setattr(
            _service,
            "_resolve",
            lambda source, dataset: SimpleNamespace(asset=SimpleNamespace(get_dra_mount=lambda: f"mount:{dataset}")),
        )
        return _service

    def test_file_session_is_never_refreshed(self, service, source, monkeypatch):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _spy = MagicMock()
        monkeypatch.setattr(DRASession, "refresh", _spy)
        service.query(_ALICE, _SQL)
        service.query(_ALICE, _SQL)
        _spy.assert_not_called()

    def test_stale_session_is_refreshed_with_fresh_mounts(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=time.monotonic() - 1000)
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=60)
        try:
            _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        _session.refresh.assert_called_once_with({"src.alpha": "mount:alpha"})

    def test_recent_session_is_not_refreshed(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=time.monotonic())
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=3600)
        try:
            _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        _session.refresh.assert_not_called()
        _session.query.assert_called_once()

    def test_zero_interval_refreshes_before_every_query(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=time.monotonic())
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=0)
        try:
            _service.query(_ALICE, _SQL)
            _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        assert _session.refresh.call_count == 2

    def test_refresh_runs_before_the_query(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=0.0)
        _order: list[str] = []
        _result = _session.query.return_value

        def _query(sql):
            _order.append("query")
            return _result

        _session.refresh.side_effect = lambda mounts: _order.append("refresh")
        _session.query.side_effect = _query
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=0)
        try:
            _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        assert _order == ["refresh", "query"]

    def test_refresh_error_fails_the_query_and_is_logged(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=0.0)
        _session.refresh.side_effect = DRARefreshError("cannot refresh credentials of src.alpha: IOException")
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=0)
        try:
            with pytest.raises(DRARefreshError):
                _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        _session.query.assert_not_called()
        assert log.warning.call_args.kwargs["metadata"]["error"] == "DRARefreshError"

    def test_provider_failure_becomes_a_refresh_error_without_its_message(self, log, monkeypatch):
        _session = self._fake_session(refreshed_at=0.0)
        _service = self._serve(monkeypatch, _session, refresh_interval_seconds=0)

        def _boom(source, dataset):
            raise RuntimeError("secret-token-xyz")

        monkeypatch.setattr(_service, "_resolve", _boom)
        try:
            with pytest.raises(DRARefreshError) as _info:
                _service.query(_ALICE, _SQL)
        finally:
            _service.stop()
        assert "secret-token-xyz" not in str(_info.value)
        assert "RuntimeError" in str(_info.value)
        _session.query.assert_not_called()


@pytest.fixture
def pooled(log, source):
    _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
    _services: list[NodeService] = []

    def _make(**dra):
        _service = NodeService(NodeServiceSetting(dra=dra))
        _service.start()
        _services.append(_service)
        return _service

    yield _make
    for _service in _services:
        _service.stop()


class TestSessionPool:
    def test_pool_limits_come_from_the_setting(self, pooled):
        _service = pooled(max_sessions=1)
        _service.query(_ALICE, _SQL)
        _service.query(_BOB, _SQL)
        assert _service._pool.keys() == ["bob"]

    def test_eviction_is_logged(self, pooled, log):
        _service = pooled(max_sessions=1)
        _service.query(_ALICE, _SQL)
        _service.query(_BOB, _SQL)
        _meta = [c.kwargs.get("metadata", {}) for c in log.info.call_args_list]
        assert {"caller": "alice", "reason": "lru"} in _meta

    def test_a_busy_pool_rejects_and_logs(self, pooled, log):
        _service = pooled(max_sessions=1)
        with _service._pool.lease("alice"):
            with pytest.raises(DRABusyError):
                _service.query(_BOB, _SQL)
        assert log.warning.call_args.kwargs["metadata"]["error"] == "DRABusyError"

    def test_health_counts_busy_sessions(self, pooled):
        _service = pooled()
        _service.query(_ALICE, _SQL)
        with _service._pool.lease("bob"):
            _health = _service.health()
        assert _health["sessions"] == 2
        assert _health["busy_sessions"] == 1

    def test_a_failed_query_releases_the_session(self, pooled):
        _service = pooled(max_sessions=1)
        with pytest.raises(DRARejectedError):
            _service.query(_ALICE, "DROP TABLE x")
        assert _service.health()["busy_sessions"] == 0
