from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.resource.compute._common._run import ComputeRun


def _make_run(**kwargs) -> ComputeRun:
    return ComputeRun(compute="demo", runtime=ComputeRuntime.PYENTRYPOINT, **kwargs)


class TestComputeRunDefaults:
    def test_defaults(self):
        _run = _make_run()
        assert _run.status == ComputeStatus.STARTED
        assert _run.id.startswith("run")
        assert _run.payload == {}
        assert _run.result == {}
        assert _run.error is None
        assert _run.external_id is None
        assert _run.finished_at is None
        assert not _run.is_finished

    def test_ids_are_unique(self):
        assert _make_run().id != _make_run().id

    def test_started_at_defaults_to_creation_time(self):
        assert _make_run().started_at is not None

    def test_explicit_started_at_is_kept(self):
        assert _make_run(started_at=123.0).started_at == 123.0

    def test_empty_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _make_run(id="")

    def test_compute_and_runtime_are_required(self):
        with pytest.raises(ValidationError):
            ComputeRun()  # type: ignore[call-arg]


class TestComputeRunTransitions:
    def test_complete(self):
        _run = _make_run()
        _run.complete({"a": 1})
        assert _run.status == ComputeStatus.COMPLETED
        assert _run.result == {"a": 1}
        assert _run.error is None
        assert _run.finished_at is not None
        assert _run.is_finished

    def test_complete_without_result_gives_empty_dict(self):
        _run = _make_run()
        _run.complete()
        assert _run.result == {}

    def test_fail_with_exception(self):
        _run = _make_run()
        _run.fail(ValueError("bad"))
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "bad"
        assert _run.is_finished

    def test_fail_without_error_uses_unknown(self):
        _run = _make_run()
        _run.fail()
        assert _run.error == "Unknown error"

    def test_cancel(self):
        _run = _make_run()
        _run.cancel()
        assert _run.status == ComputeStatus.CANCELLED
        assert _run.error is None
        assert _run.is_finished

    @pytest.mark.parametrize("action", ["complete", "fail", "cancel"])
    @pytest.mark.parametrize("first", ["complete", "fail", "cancel"])
    def test_finished_run_cannot_transit_again(self, first, action):
        _run = _make_run()
        getattr(_run, first)()
        with pytest.raises(ValueError):
            getattr(_run, action)()


class TestComputeRunSubmit:
    def test_submit_sets_external_id_and_keeps_started(self):
        _run = _make_run()
        _run.submit("ext-1")
        assert _run.external_id == "ext-1"
        assert _run.status == ComputeStatus.STARTED
        assert _run.finished_at is None
        assert _run.error is None


class TestComputeRunDuration:
    def test_finished_duration_is_fixed(self):
        _run = _make_run(started_at=100.0)
        _run.complete()
        _run.finished_at = 130.0
        assert _run.duration == 30.0

    def test_running_duration_is_positive(self):
        assert _make_run(started_at=0.0).duration > 0


class TestComputeRunSerialisation:
    def test_export_and_from_dict_round_trip(self):
        _run = _make_run(payload={"a": 1})
        _run.submit("ext-1")
        _run.complete({"b": 2})
        _restored = ComputeRun.from_dict(_run.export())
        assert _restored.id == _run.id
        assert _restored.status == ComputeStatus.COMPLETED
        assert _restored.payload == {"a": 1}
        assert _restored.result == {"b": 2}
        assert _restored.external_id == "ext-1"
        assert _restored.started_at == _run.started_at
        assert _restored.finished_at == _run.finished_at
