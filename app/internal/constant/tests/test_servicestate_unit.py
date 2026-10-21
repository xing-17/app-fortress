from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.servicestate import ServiceState


class TestServiceStateValues:
    def test_created_value(self):
        assert ServiceState.CREATED == "created"

    def test_starting_value(self):
        assert ServiceState.STARTING == "starting"

    def test_running_value(self):
        assert ServiceState.RUNNING == "running"

    def test_stopping_value(self):
        assert ServiceState.STOPPING == "stopping"

    def test_stopped_value(self):
        assert ServiceState.STOPPED == "stopped"

    def test_failed_value(self):
        assert ServiceState.FAILED == "failed"

    def test_members_count(self):
        assert len(ServiceState) == 6

    def test_values_are_unique(self):
        values = [m.value for m in ServiceState]
        assert len(values) == len(set(values))


class TestServiceStateBehaviour:
    def test_is_str_enum(self):
        assert issubclass(ServiceState, StrEnum)

    def test_str_returns_value(self):
        assert str(ServiceState.RUNNING) == "running"

    def test_lookup_by_value(self):
        assert ServiceState("failed") is ServiceState.FAILED

    def test_lookup_by_name(self):
        assert ServiceState["STOPPED"] is ServiceState.STOPPED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ServiceState("invalid")

    def test_value_is_case_sensitive(self):
        with pytest.raises(ValueError):
            ServiceState("RUNNING")

    def test_exported_from_constant_package(self):
        from app.internal.constant import ServiceState as Exported

        assert Exported is ServiceState
