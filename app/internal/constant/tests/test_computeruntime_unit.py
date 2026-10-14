from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.computeruntime import ComputeRuntime


class TestComputeRuntimeValues:
    def test_pyentrypoint_value(self):
        assert ComputeRuntime.PYENTRYPOINT == "pyentrypoint"

    def test_fc_value(self):
        assert ComputeRuntime.FC == "fc"

    def test_members_count(self):
        assert len(ComputeRuntime) == 2


class TestComputeRuntimeBehaviour:
    def test_is_str_enum(self):
        assert issubclass(ComputeRuntime, StrEnum)

    def test_lookup_by_value(self):
        assert ComputeRuntime("fc") is ComputeRuntime.FC

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ComputeRuntime("invalid")
