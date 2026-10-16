from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._run import ComputeRun
from app.resource.store.file.store import FileStore


class _FakeCompute(BaseCompute):
    runtime = ComputeRuntime.PYENTRYPOINT
    platform = Platform.LOCAL

    @classmethod
    def from_setting(cls, setting) -> "_FakeCompute":
        return cls(name=setting.name)

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("boom"):
            raise RuntimeError("boom")
        return {"echo": payload}

    def _submit(self, payload: dict[str, Any]) -> str:
        if payload.get("boom"):
            raise RuntimeError("boom")
        return "ext-1"

    def _poll(self, run: ComputeRun) -> ComputeRun:
        run.complete({"polled": True})
        return run


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _make_compute(tmp_path, name: str = "demo", **kwargs) -> _FakeCompute:
    return _FakeCompute(name=name, store=FileStore(name="s", path=str(tmp_path)), **kwargs)


class TestBaseComputeConstruction:
    def test_invalid_name_raises_validation_error(self, tmp_path):
        with pytest.raises(ValidationError):
            _make_compute(tmp_path, name="bad-name")

    def test_max_run_records_must_be_positive(self, tmp_path):
        with pytest.raises(ValidationError):
            _make_compute(tmp_path, max_run_records=0)

    def test_table_is_derived(self, tmp_path):
        assert _make_compute(tmp_path).table is not None

    def test_frn_contains_platform_runtime_and_name(self, tmp_path):
        _frn = _make_compute(tmp_path).frn
        assert "platform=local" in _frn
        assert "runtime=pyentrypoint" in _frn
        assert "name=demo" in _frn


class TestBaseComputeExecute:
    def test_success_records_completed_run(self, tmp_path):
        _c = _make_compute(tmp_path)
        _run = _c.execute({"a": 1})
        assert _run.status == ComputeStatus.COMPLETED
        assert _run.result == {"echo": {"a": 1}}
        assert _c.lookup(_run.id).status == ComputeStatus.COMPLETED

    def test_none_payload_becomes_empty_dict(self, tmp_path):
        assert _make_compute(tmp_path).execute().payload == {}

    def test_failure_is_recorded_and_not_raised_by_default(self, tmp_path):
        _c = _make_compute(tmp_path)
        _run = _c.execute({"boom": True})
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "RuntimeError: boom"
        assert _c.lookup(_run.id).status == ComputeStatus.FAILED

    def test_failure_raises_when_requested_and_still_recorded(self, tmp_path):
        _c = _make_compute(tmp_path)
        with pytest.raises(RuntimeError):
            _c.execute({"boom": True}, raise_on_error=True)
        _runs = _c.list_runs()
        assert len(_runs) == 1
        assert _runs[0].status == ComputeStatus.FAILED

    def test_non_dict_payload_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            _make_compute(tmp_path).execute(["x"])  # type: ignore[arg-type]

    def test_non_serialisable_payload_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            _make_compute(tmp_path).execute({"x": object()})


class TestBaseComputeSubmit:
    def test_success_records_started_run_with_external_id(self, tmp_path):
        _c = _make_compute(tmp_path)
        _run = _c.submit({"a": 1})
        assert _run.status == ComputeStatus.STARTED
        assert _run.external_id == "ext-1"
        assert _c.lookup(_run.id).external_id == "ext-1"

    def test_failure_is_recorded_and_not_raised_by_default(self, tmp_path):
        _run = _make_compute(tmp_path).submit({"boom": True})
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "RuntimeError: boom"

    def test_failure_raises_when_requested(self, tmp_path):
        with pytest.raises(RuntimeError):
            _make_compute(tmp_path).submit({"boom": True}, raise_on_error=True)


class TestBaseComputeRefresh:
    def test_refresh_by_id_records_terminal_status(self, tmp_path):
        _c = _make_compute(tmp_path)
        _run = _c.submit()
        _refreshed = _c.refresh(_run.id)
        assert _refreshed.status == ComputeStatus.COMPLETED
        assert _c.lookup(_run.id).result == {"polled": True}

    def test_refresh_by_run_object(self, tmp_path):
        _c = _make_compute(tmp_path)
        assert _c.refresh(_c.submit()).status == ComputeStatus.COMPLETED

    def test_refresh_finished_run_does_not_poll(self, tmp_path):
        _c = _make_compute(tmp_path)
        _run = _c.execute()
        assert _c.refresh(_run).result == {"echo": {}}

    def test_refresh_unknown_id_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            _make_compute(tmp_path).refresh("missing")

    def test_refresh_invalid_type_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            _make_compute(tmp_path).refresh(123)  # type: ignore[arg-type]


class TestBaseComputeLookupAndList:
    def test_lookup_unknown_returns_none(self, tmp_path):
        assert _make_compute(tmp_path).lookup("missing") is None

    def test_list_runs_empty(self, tmp_path):
        assert _make_compute(tmp_path).list_runs() == []

    def test_list_runs_newest_first(self, tmp_path):
        _c = _make_compute(tmp_path)
        _ids = [_c.execute().id for _ in range(3)]
        _runs = _c.list_runs()
        assert [_r.id for _r in _runs] == _ids[::-1]

    def test_list_runs_filters_by_status(self, tmp_path):
        _c = _make_compute(tmp_path)
        _c.execute()
        _c.execute({"boom": True})
        _c.submit()
        assert len(_c.list_runs(status=ComputeStatus.COMPLETED)) == 1
        assert len(_c.list_runs(status=ComputeStatus.FAILED)) == 1
        assert len(_c.list_runs(status=ComputeStatus.STARTED)) == 1

    def test_list_runs_limit(self, tmp_path):
        _c = _make_compute(tmp_path)
        for _ in range(3):
            _c.execute()
        assert len(_c.list_runs(limit=2)) == 2

    def test_runs_are_isolated_between_computes(self, tmp_path):
        _a = _make_compute(tmp_path, name="a")
        _b = _make_compute(tmp_path, name="b")
        _a.execute()
        assert _b.list_runs() == []
