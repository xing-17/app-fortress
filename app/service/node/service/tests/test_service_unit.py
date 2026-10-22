from __future__ import annotations

import io
from unittest.mock import MagicMock

import polars as pl
import pytest

from app.internal.logstream import LogStream
from app.internal.model.dra import DRARejectedError
from app.resource._global.identities import GlobalIdentities
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.sources import GlobalSources
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common.tests.fakes.base import FakeSource
from app.resource.store.file.store import FileStore
from app.service.node.service.auth import Principal
from app.service.node.service.errors import NodeDatasetNotFoundError, NodeSourceNotFoundError
from app.service.node.service.service import NodeService
from app.setting.service import NodeServiceSetting


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
        _first = service._sessions["alice"]
        service.query(_ALICE, "SELECT * FROM src.alpha")
        assert service._sessions["alice"] is _first

    def test_callers_get_isolated_sessions(self, service, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        service.query(_ALICE, "SELECT * FROM src.alpha")
        service.query(_BOB, "SELECT * FROM src.alpha")
        assert service._sessions["alice"] is not service._sessions["bob"]

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
        _first = service._sessions["alice"]
        service.reset_sessions()
        service.query(_ALICE, "SELECT * FROM src.alpha")
        assert service._sessions["alice"] is not _first

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
