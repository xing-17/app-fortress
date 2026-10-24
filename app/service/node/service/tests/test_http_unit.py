from __future__ import annotations

import io
import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import polars as pl
import pytest
from starlette.testclient import TestClient

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.sources import GlobalSources
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common.tests.fakes.base import FakeDataset, FakeSource
from app.resource.store.file.store import FileStore
from app.service._common.auth import TokenAuth
from app.service.node.dra import (
    DRABusyError,
    DRAError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.http import create_app
from app.service.node.service.service import NodeService
from app.setting.service import AuthSetting, NodeServiceSetting

_KEY = "k" * 64


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


@pytest.fixture
def auth(tmp_path):
    _key = tmp_path / "password.key"
    _key.write_text(_KEY + "\n", encoding="utf-8")
    _key.chmod(0o600)
    _setting = AuthSetting(
        masterfile=str(_key),
        tokens=[
            {"name": "alice"},
            {"name": "gone", "revoked": True},
            {"name": "host", "delegate": True},
        ],
    )
    return TokenAuth(_setting)


@pytest.fixture
def client(service, auth):
    return TestClient(create_app(service, auth), raise_server_exceptions=False)


@pytest.fixture
def headers(auth):
    return {"Authorization": f"Bearer {auth.token('alice')}"}


def _write(source, dataset_name, name, df, partitions=None, metadata=True):
    _dataset = source.dataset(dataset_name)
    _file = _dataset.asset.assetfile(name, partitions=partitions)
    _buffer = io.BytesIO()
    df.write_parquet(_buffer)
    _dataset.write_assetfile(_file, _buffer.getvalue())
    if metadata:
        _dataset.write_metadata(_file, _dataset.get_metadata(df))
    return _file


class TestAuth:
    def test_health_needs_no_token(self, client):
        _res = client.get("/health")
        assert _res.status_code == 200
        assert _res.json()["is_running"] is True

    def test_health_is_503_when_not_running(self, client, service):
        service.stop()
        assert client.get("/health").status_code == 503

    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer " + "0" * 64},
            {"Authorization": "Basic abc"},
            {"Authorization": "Bearer short"},
        ],
    )
    def test_bad_tokens_get_the_same_401(self, client, headers):
        _res = client.get("/internal/sources", headers=headers)
        assert _res.status_code == 401
        assert _res.json() == {"error": "unauthorized"}
        assert _res.headers["www-authenticate"] == "Bearer"

    def test_revoked_token_looks_like_any_other(self, client, auth, log):
        _state = auth._state
        _token = auth._mac(_state.masterkey, _state.entries["gone"])
        _res = client.get("/internal/sources", headers={"Authorization": f"Bearer {_token}"})
        assert _res.status_code == 401
        assert _res.json() == {"error": "unauthorized"}

    def test_reason_goes_to_the_log_only(self, client, log):
        client.get("/internal/sources", headers={"Authorization": "Bearer " + "0" * 64})
        _kwargs = log.warning.call_args.kwargs
        assert _kwargs["metadata"]["reason"] == "mismatch"

    def test_unknown_path_without_token_is_401(self, client):
        assert client.get("/nope").status_code == 401

    def test_valid_token_passes(self, client, headers):
        assert client.get("/internal/sources", headers=headers).status_code == 200


class TestCatalog:
    def test_sources(self, client, headers):
        _res = client.get("/internal/sources", headers=headers).json()
        assert [s["name"] for s in _res] == ["src"]

    def test_source(self, client, headers):
        assert client.get("/internal/sources/src", headers=headers).json()["name"] == "src"

    def test_unknown_source_is_404(self, client, headers):
        _res = client.get("/internal/sources/nope", headers=headers)
        assert _res.status_code == 404
        assert _res.json()["error"] == "NodeSourceNotFoundError"

    def test_datasets_all_and_filtered(self, client, headers):
        _all = client.get("/internal/datasets", headers=headers).json()
        assert sorted(d["dataset"] for d in _all) == ["src.alpha", "src.beta"]
        _one = client.get("/internal/datasets", params={"source": "src"}, headers=headers).json()
        assert len(_one) == 2
        assert client.get("/internal/datasets", params={"source": "x"}, headers=headers).status_code == 404

    def test_dataset(self, client, headers):
        _res = client.get("/internal/datasets/src/beta", headers=headers).json()
        assert _res["dataset"] == "src.beta"

    def test_unknown_dataset_is_404(self, client, headers):
        _res = client.get("/internal/datasets/src/nope", headers=headers)
        assert _res.status_code == 404
        assert _res.json()["error"] == "NodeDatasetNotFoundError"


class TestAssetfiles:
    def test_modified_at_is_epoch_seconds(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = client.get("/internal/datasets/src/alpha/assetfiles", headers=headers).json()
        assert isinstance(_res[0]["modified_at"], float)

    def test_since_in_the_future_filters_everything(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _url = "/internal/datasets/src/alpha/assetfiles"
        assert client.get(_url, params={"since": 4_000_000_000}, headers=headers).json() == []
        assert len(client.get(_url, params={"until": 4_000_000_000}, headers=headers).json()) == 1

    def test_iso_datetime_is_accepted(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _url = "/internal/datasets/src/alpha/assetfiles"
        _res = client.get(_url, params={"since": "2999-01-01T00:00:00+00:00"}, headers=headers)
        assert _res.status_code == 200
        assert _res.json() == []

    def test_naive_iso_datetime_is_read_as_utc(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _url = "/internal/datasets/src/alpha/assetfiles"
        _modified = client.get(_url, headers=headers).json()[0]["modified_at"]
        _after = datetime.fromtimestamp(_modified + 3600, tz=timezone.utc).replace(tzinfo=None)
        _before = datetime.fromtimestamp(_modified - 3600, tz=timezone.utc).replace(tzinfo=None)
        assert client.get(_url, params={"since": _after.isoformat()}, headers=headers).json() == []
        assert len(client.get(_url, params={"since": _before.isoformat()}, headers=headers).json()) == 1

    def test_bad_time_is_400(self, client, headers):
        _res = client.get("/internal/datasets/src/alpha/assetfiles", params={"since": "yesterday"}, headers=headers)
        assert _res.status_code == 400


class TestMetadata:
    def test_metadatas(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = client.get("/internal/datasets/src/alpha/metadatas", headers=headers).json()
        assert set(_res[0]["metadata"]) == {"quality", "definition"}

    def test_qualities(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = client.get("/internal/datasets/src/alpha/qualities", headers=headers).json()
        assert _res[0]["quality"]["height"] == 3

    def test_definitions(self, client, headers, source):
        _write(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        _res = client.get("/internal/datasets/src/beta/definitions", headers=headers).json()
        assert _res[0]["partitions"] == [{"year": "2023"}]


class TestRuns:
    _URL = "/internal/datasets/src/alpha/runs"

    def test_lists_the_runs(self, client, headers, source):
        source.dataset("alpha").run()
        _res = client.get(self._URL, headers=headers)
        assert _res.status_code == 200
        assert [r["status"] for r in _res.json()] == ["completed"]

    def test_status_and_limit_are_applied(self, client, headers, source):
        _dataset = source.dataset("alpha")
        _dataset.run()
        _dataset.run()
        assert len(client.get(self._URL, params={"limit": "1"}, headers=headers).json()) == 1
        assert client.get(self._URL, params={"status": "failed"}, headers=headers).json() == []

    def test_needs_a_token(self, client):
        assert client.get(self._URL).status_code == 401

    @pytest.mark.parametrize("params", [{"limit": "abc"}, {"limit": "0"}, {"status": "nope"}])
    def test_bad_parameters_are_a_400(self, client, headers, params):
        _res = client.get(self._URL, params=params, headers=headers)
        assert _res.status_code == 400
        assert _res.json()["error"] == "NodeBadRequestError"

    def test_unknown_dataset_is_404(self, client, headers):
        assert client.get("/internal/datasets/src/nope/runs", headers=headers).status_code == 404


class TestSubmitAndGetRun:
    _URL = "/internal/datasets/src/alpha/runs"

    @pytest.fixture
    def gate(self, monkeypatch):
        # Every dataset run blocks in extract until the gate opens
        _gate = threading.Event()

        def _extract(self, params=None):
            _gate.wait(10)
            return pl.DataFrame({"a": [1]})

        monkeypatch.setattr(FakeDataset, "extract", _extract)
        yield _gate
        _gate.set()

    def test_submit_answers_202_with_a_started_record(self, client, headers, gate):
        _res = client.post(self._URL, json={"params": {"k": "v"}}, headers=headers)
        assert _res.status_code == 202
        assert _res.json()["status"] == "started"
        assert _res.json()["params"] == {"k": "v"}

    def test_submit_without_a_body_runs_with_no_params(self, client, headers, gate):
        _res = client.post(self._URL, headers=headers)
        assert _res.status_code == 202
        assert not _res.json()["params"]

    def test_run_can_be_polled_until_it_completes(self, client, headers, gate):
        _id = client.post(self._URL, headers=headers).json()["id"]
        assert client.get(f"{self._URL}/{_id}", headers=headers).json()["status"] == "started"
        gate.set()
        for _ in range(200):
            _res = client.get(f"{self._URL}/{_id}", headers=headers).json()
            if _res["status"] != "started":
                break
            time.sleep(0.05)
        assert _res["status"] == "completed"

    def test_same_dataset_twice_is_503(self, client, headers, gate):
        client.post(self._URL, headers=headers)
        _res = client.post(self._URL, headers=headers)
        assert _res.status_code == 503
        assert _res.json()["error"] == "NodeBusyError"

    def test_unknown_run_is_404(self, client, headers):
        _res = client.get(f"{self._URL}/run-missing", headers=headers)
        assert _res.status_code == 404
        assert _res.json()["error"] == "NodeRunNotFoundError"

    def test_unknown_dataset_is_404(self, client, headers):
        assert client.post("/internal/datasets/src/nope/runs", headers=headers).status_code == 404
        assert client.get("/internal/datasets/src/nope/runs/x", headers=headers).status_code == 404

    @pytest.mark.parametrize("body", ["not json", "[1]", '{"params": [1]}'])
    def test_bad_body_is_400(self, client, headers, body):
        _res = client.post(self._URL, content=body, headers=headers)
        assert _res.status_code == 400
        assert _res.json()["error"] == "NodeBadRequestError"

    def test_too_large_body_is_413(self, client, headers):
        _res = client.post(self._URL, content=b"x" * 1_000_001, headers=headers)
        assert _res.status_code == 413

    def test_both_routes_need_a_token(self, client):
        assert client.post(self._URL).status_code == 401
        assert client.get(f"{self._URL}/x").status_code == 401


class TestMachine:
    _URL = "/internal/machine/snapshots"

    def test_needs_a_token(self, client):
        assert client.get(self._URL).status_code == 401

    def test_lists_the_snapshots(self, client, headers, service):
        service._machine._record()
        _res = client.get(self._URL, headers=headers)
        assert _res.status_code == 200
        assert len(_res.json()) == 1

    def test_hours_narrows_the_window(self, client, headers, service):
        service._machine._record()
        _res = client.get(self._URL, params={"hours": "1"}, headers=headers)
        assert len(_res.json()) == 1

    @pytest.mark.parametrize("hours", ["abc", "0", "-2"])
    def test_bad_hours_is_a_400(self, client, headers, hours):
        _res = client.get(self._URL, params={"hours": hours}, headers=headers)
        assert _res.status_code == 400
        assert _res.json()["error"] == "NodeBadRequestError"


class TestQuery:
    def test_runs_a_select(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2]}))
        _res = client.post("/internal/query", json={"sql": "SELECT a FROM src.alpha ORDER BY a"}, headers=headers)
        assert _res.status_code == 200
        _body = _res.json()
        assert _body["columns"] == ["a"]
        assert _body["rows"] == [[1], [2]]
        assert _body["truncated"] is False

    def test_nan_and_temporal_values_are_valid_json(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _sql = "SELECT 'nan'::DOUBLE AS x, TIMESTAMP '2025-01-02 03:04:05' AS t, 1.5::DECIMAL(5,2) AS d FROM src.alpha"
        _res = client.post("/internal/query", json={"sql": _sql}, headers=headers)
        assert _res.status_code == 200
        _row = _res.json()["rows"][0]
        assert _row[0] is None
        assert _row[1].startswith("2025-01-02T03:04:05")
        assert _row[2] == "1.50"

    def test_caller_is_the_token_name(self, client, headers, source, service, monkeypatch):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _seen = []
        _orig = service.query
        monkeypatch.setattr(service, "query", lambda caller, sql: (_seen.append(caller.name), _orig(caller, sql))[1])
        client.post("/internal/query", json={"sql": "SELECT 1"}, headers=headers)
        assert _seen == ["alice"]


class TestDelegation:
    def _caller_of(self, client, headers, service, monkeypatch):
        _seen = []
        _orig = service.query
        monkeypatch.setattr(service, "query", lambda caller, sql: (_seen.append(caller.name), _orig(caller, sql))[1])
        _res = client.post("/internal/query", json={"sql": "SELECT 1"}, headers=headers)
        return _res, _seen

    def test_a_delegating_token_acts_for_the_named_caller(self, client, auth, service, monkeypatch):
        _headers = {"Authorization": f"Bearer {auth.token('host')}", "X-Fortress-Caller": "phone"}
        _res, _seen = self._caller_of(client, _headers, service, monkeypatch)
        assert _seen == ["host:phone"]

    def test_without_the_header_the_token_is_the_caller(self, client, auth, service, monkeypatch):
        _headers = {"Authorization": f"Bearer {auth.token('host')}"}
        _res, _seen = self._caller_of(client, _headers, service, monkeypatch)
        assert _seen == ["host"]

    def test_other_tokens_cannot_name_a_caller(self, client, headers, log):
        _res = client.get("/internal/sources", headers={**headers, "X-Fortress-Caller": "phone"})
        assert _res.status_code == 401
        assert _res.json() == {"error": "unauthorized"}
        assert log.warning.call_args.kwargs["metadata"]["reason"] == "delegation denied"

    @pytest.mark.parametrize("caller", ["", "Phone", "a:b", "a b", "-a", "x" * 33])
    def test_a_malformed_caller_is_rejected(self, client, auth, caller, log):
        _headers = {"Authorization": f"Bearer {auth.token('host')}", "X-Fortress-Caller": caller}
        _res = client.get("/internal/sources", headers=_headers)
        assert _res.status_code == 401

    @pytest.mark.parametrize(
        "body",
        [b"not json", b"[]", b'{"sql": 1}', b'{"sql": "  "}', b"{}"],
    )
    def test_malformed_body_is_400(self, client, headers, body):
        _res = client.post("/internal/query", content=body, headers=headers)
        assert _res.status_code == 400

    def test_rejected_statement_is_400(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = client.post("/internal/query", json={"sql": "DROP TABLE x"}, headers=headers)
        assert _res.status_code == 400
        assert _res.json()["error"] == "DRARejectedError"

    def test_engine_error_is_400(self, client, headers, source):
        _write(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _res = client.post("/internal/query", json={"sql": "SELECT nope FROM src.alpha"}, headers=headers)
        assert _res.status_code == 400
        assert _res.json()["error"] == "DRAQueryError"

    def test_too_large_body_is_413(self, client, headers):
        _res = client.post("/internal/query", json={"sql": "SELECT " + "1," * 600_000 + "1"}, headers=headers)
        assert _res.status_code == 413

    def test_requires_post(self, client, headers):
        assert client.get("/internal/query", headers=headers).status_code == 405


class TestErrorMapping:
    @pytest.mark.parametrize(
        ("exc", "status"),
        [
            (DRARejectedError("x"), 400),
            (DRAQueryError("x"), 400),
            (DRAQueryTimeoutError("x"), 408),
            (DRABusyError("x"), 503),
            (DRAError("x"), 500),
            (RuntimeError("secret detail"), 500),
        ],
    )
    def test_status(self, client, headers, service, monkeypatch, exc, status):
        def _raise(caller, sql):
            raise exc

        monkeypatch.setattr(service, "query", _raise)
        _res = client.post("/internal/query", json={"sql": "SELECT 1"}, headers=headers)
        assert _res.status_code == status

    def test_unexpected_error_hides_detail_and_is_logged(self, client, headers, service, log, monkeypatch):
        def _raise(caller, sql):
            raise RuntimeError("secret detail")

        monkeypatch.setattr(service, "query", _raise)
        _res = client.post("/internal/query", json={"sql": "SELECT 1"}, headers=headers)
        assert _res.status_code == 500
        assert "secret" not in _res.text
        assert log.error.called
