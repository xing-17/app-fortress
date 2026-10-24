from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.computestatus import ComputeStatus
from app.resource.source._common._run import DatasetRun


def _make_run(**kwargs) -> DatasetRun:
    return DatasetRun(provider="tushare", dataset="alpha", **kwargs)


class TestDatasetRunDefaults:
    def test_defaults(self):
        _run = _make_run()
        assert _run.status == ComputeStatus.STARTED
        assert _run.id.startswith("run")
        assert _run.params == {}
        assert _run.assetfiles == []
        assert _run.height is None
        assert _run.width is None
        assert _run.error is None
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

    def test_provider_and_dataset_are_required(self):
        with pytest.raises(ValidationError):
            DatasetRun()  # type: ignore[call-arg]


class TestDatasetRunTransitions:
    def test_complete(self):
        _run = _make_run()
        _run.complete(assetfiles=["a.parquet"], height=3, width=2)
        assert _run.status == ComputeStatus.COMPLETED
        assert _run.assetfiles == ["a.parquet"]
        assert _run.height == 3
        assert _run.width == 2
        assert _run.error is None
        assert _run.finished_at is not None
        assert _run.is_finished

    def test_fail_with_exception(self):
        _run = _make_run()
        _run.fail(ValueError("bad"))
        assert _run.status == ComputeStatus.FAILED
        assert _run.error == "bad"
        assert _run.finished_at is not None
        assert _run.is_finished

    def test_fail_without_error_uses_unknown(self):
        _run = _make_run()
        _run.fail()
        assert _run.error == "Unknown error"

    @pytest.mark.parametrize("action", ["complete", "fail"])
    @pytest.mark.parametrize("first", ["complete", "fail"])
    def test_finished_run_cannot_transit_again(self, first, action):
        _run = _make_run()
        _calls = {
            "complete": lambda: _run.complete(assetfiles=[], height=0, width=0),
            "fail": lambda: _run.fail("x"),
        }
        _calls[first]()
        with pytest.raises(ValueError):
            _calls[action]()


class TestDatasetRunDuration:
    def test_finished_duration_is_fixed(self):
        _run = _make_run(started_at=100.0)
        _run.complete(assetfiles=[], height=0, width=0)
        _run.finished_at = 130.0
        assert _run.duration == 30.0

    def test_running_duration_is_positive(self):
        assert _make_run(started_at=0.0).duration > 0


class TestDatasetRunSerialisation:
    def test_export_and_from_dict_round_trip(self):
        _run = _make_run(params={"k": "v"})
        _run.complete(assetfiles=["a.parquet"], height=3, width=2)
        _restored = DatasetRun.from_dict(_run.export())
        assert _restored.id == _run.id
        assert _restored.status == ComputeStatus.COMPLETED
        assert _restored.params == {"k": "v"}
        assert _restored.assetfiles == ["a.parquet"]
        assert _restored.height == 3
        assert _restored.width == 2
        assert _restored.started_at == _run.started_at
        assert _restored.finished_at == _run.finished_at
