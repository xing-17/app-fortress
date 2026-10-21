from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.servicekind import ServiceKind


class TestServiceKindValues:
    def test_machine_value(self):
        assert ServiceKind.MACHINE == "machine"

    def test_node_value(self):
        assert ServiceKind.NODE == "node"

    def test_mcphost_value(self):
        assert ServiceKind.MCPHOST == "mcphost"

    def test_webhost_value(self):
        assert ServiceKind.WEBHOST == "webhost"

    def test_members_count(self):
        assert len(ServiceKind) == 4

    def test_values_are_unique(self):
        values = [m.value for m in ServiceKind]
        assert len(values) == len(set(values))


class TestServiceKindBehaviour:
    def test_is_str_enum(self):
        assert issubclass(ServiceKind, StrEnum)

    def test_str_returns_value(self):
        assert str(ServiceKind.NODE) == "node"

    def test_lookup_by_value(self):
        assert ServiceKind("mcphost") is ServiceKind.MCPHOST

    def test_lookup_by_name(self):
        assert ServiceKind["WEBHOST"] is ServiceKind.WEBHOST

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ServiceKind("invalid")

    def test_value_is_case_sensitive(self):
        with pytest.raises(ValueError):
            ServiceKind("NODE")

    def test_exported_from_constant_package(self):
        from app.internal.constant import ServiceKind as Exported

        assert Exported is ServiceKind
