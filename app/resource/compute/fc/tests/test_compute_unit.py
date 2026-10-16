from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.platform import Platform
from app.resource._client.fc.client import FCClient
from app.resource._global.identities import GlobalIdentities
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._run import ComputeRun
from app.resource.compute.fc import FCCompute
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store.file.store import FileStore

_clients: dict[str, MagicMock] = {}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    GlobalIdentities.reset()
    # the cache lookup is patched so no test builds a real SDK client
    monkeypatch.setattr(FCClient, "get_client", classmethod(lambda cls, **_kw: _clients["current"]))
    yield
    _clients.clear()
    GlobalIdentities.reset()


def _make(tmp_path: Path, client: MagicMock, **kwargs: Any) -> FCCompute:
    _clients["current"] = client
    return FCCompute(
        name="demo",
        function_name="fortress-run",
        region="cn-hangzhou",
        identity=AliyunIdentity.default(),
        store=FileStore(name="s", path=str(tmp_path / "store")),
        **kwargs,
    )


def _reply(body: Any = None, error: str | None = None) -> dict[str, Any]:
    return {"request_id": "req-1", "status_code": 200, "body": {} if body is None else body, "error": error}


def _wait(compute: FCCompute, run: ComputeRun, timeout: float = 5.0) -> ComputeRun:
    _deadline = time.monotonic() + timeout
    while not run.is_finished:
        assert time.monotonic() < _deadline, "run did not finish"
        run = compute.refresh(run)
        time.sleep(0.01)
    return run


class TestConstruction:
    def test_class_variables(self):
        assert FCCompute.runtime == ComputeRuntime.FC
        assert FCCompute.platform == Platform.ALIYUN

    def test_is_a_base_compute(self, tmp_path):
        assert isinstance(_make(tmp_path, MagicMock()), BaseCompute)

    def test_default_timeout(self, tmp_path):
        assert _make(tmp_path, MagicMock()).timeout_seconds == 600

    def test_default_max_workers(self, tmp_path):
        assert _make(tmp_path, MagicMock()).max_workers == 8


class TestExecute:
    def test_completes_with_dict_result(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply({"rows": 3})
        _run = _make(tmp_path, _client).execute({"a": 1})
        assert _run.status == ComputeStatus.COMPLETED
        assert _run.result == {"rows": 3}
        _kwargs = _client.invoke.call_args.kwargs
        assert json.loads(_kwargs["payload"]) == {"a": 1}
        assert _kwargs["function_name"] == "fortress-run"
        assert _kwargs["qualifier"] == "LATEST"
        assert _kwargs["timeout_seconds"] == 600

    def test_empty_body_is_empty_result(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply({})
        assert _make(tmp_path, _client).execute().result == {}

    def test_function_error_fails_the_run(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply(error="boom")
        _compute = _make(tmp_path, _client)
        _run = _compute.execute()
        assert _run.status == ComputeStatus.FAILED
        assert "boom" in _run.error
        assert _compute.lookup(_run.id).status == ComputeStatus.FAILED

    def test_sdk_error_fails_the_run(self, tmp_path):
        _client = MagicMock()
        _client.invoke.side_effect = ConnectionError("down")
        _run = _make(tmp_path, _client).execute()
        assert _run.status == ComputeStatus.FAILED
        assert "down" in _run.error

    def test_raise_on_error(self, tmp_path):
        _client = MagicMock()
        _client.invoke.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            _make(tmp_path, _client).execute(raise_on_error=True)


class TestSubmit:
    def test_returns_started_run_before_the_call_finishes(self, tmp_path):
        _release = threading.Event()
        _client = MagicMock()
        _client.invoke.side_effect = lambda **_kw: (_release.wait(5), _reply({"rows": 3}))[1]
        _compute = _make(tmp_path, _client)
        _run = _compute.submit({"a": 1})
        assert _run.status == ComputeStatus.STARTED
        assert _run.external_id
        assert _compute.lookup(_run.id).external_id == _run.external_id
        assert _compute.refresh(_run).status == ComputeStatus.STARTED
        _release.set()
        _done = _wait(_compute, _run)
        assert _done.status == ComputeStatus.COMPLETED
        assert _done.result == {"rows": 3}
        assert _compute.lookup(_run.id).status == ComputeStatus.COMPLETED

    def test_failure_is_recorded_on_refresh(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply(error="boom")
        _compute = _make(tmp_path, _client)
        _done = _wait(_compute, _compute.submit())
        assert _done.status == ComputeStatus.FAILED
        assert "boom" in _done.error

    def test_refresh_by_id(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply({"ok": True})
        _compute = _make(tmp_path, _client)
        _run = _compute.submit()
        _deadline = time.monotonic() + 5
        while _compute.refresh(_run.id).status == ComputeStatus.STARTED:
            assert time.monotonic() < _deadline
            time.sleep(0.01)
        assert _compute.lookup(_run.id).result == {"ok": True}

    def test_concurrent_submits_are_independent(self, tmp_path):
        _client = MagicMock()
        _client.invoke.side_effect = lambda **kw: _reply(json.loads(kw["payload"]))
        _compute = _make(tmp_path, _client, max_workers=2)
        _runs = [_compute.submit({"n": _i}) for _i in range(6)]
        assert len({_r.external_id for _r in _runs}) == 6
        for _i, _run in enumerate(_runs):
            assert _wait(_compute, _run).result == {"n": _i}

    def test_unknown_token_after_restart_fails(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply()
        _first = _make(tmp_path, _client)
        _run = _first.submit()
        _wait(_first, _run)
        _lost = ComputeRun(compute="demo", runtime=ComputeRuntime.FC, external_id="fc-gone")
        _second = _make(tmp_path, _client)
        assert _second.refresh(_lost).status == ComputeStatus.FAILED

    def test_finished_run_is_not_failed_by_a_stale_object(self, tmp_path):
        _client = MagicMock()
        _client.invoke.return_value = _reply({"ok": True})
        _compute = _make(tmp_path, _client)
        _run = _compute.submit()
        _stale = _compute.lookup(_run.id)
        _wait(_compute, _run)
        assert _compute.refresh(_stale).status == ComputeStatus.COMPLETED


class TestExport:
    def test_identity_is_exported_by_name(self, tmp_path):
        _client = MagicMock()
        _compute = _make(tmp_path, _client)
        assert _compute.export()["identity"] == "aliyun_default_identity"
