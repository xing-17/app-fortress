from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.computestatus import ComputeStatus


class TestComputeStatusValues:
    def test_not_started_value(self):
        assert ComputeStatus.NOT_STARTED == "not_started"

    def test_started_value(self):
        assert ComputeStatus.STARTED == "started"

    def test_succeeded_value(self):
        assert ComputeStatus.SUCCEEDED == "succeeded"

    def test_failed_value(self):
        assert ComputeStatus.FAILED == "failed"

    def test_unknown_value(self):
        assert ComputeStatus.UNKNOWN == "unknown"

    def test_members_count(self):
        assert len(ComputeStatus) == 5


class TestComputeStatusBehaviour:
    def test_is_str_enum(self):
        assert issubclass(ComputeStatus, StrEnum)

    def test_lookup_by_value(self):
        assert ComputeStatus("failed") is ComputeStatus.FAILED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ComputeStatus("invalid")
