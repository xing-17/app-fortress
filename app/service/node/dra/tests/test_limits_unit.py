from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.service.node.dra import DRALimits


class TestDRALimits:
    def test_defaults(self):
        limits = DRALimits()
        assert limits.timeout_seconds == 120.0
        assert limits.max_rows == 10_000
        assert limits.max_result_mb == 128.0
        assert limits.memory_limit_mb == 1024
        assert limits.threads == 2

    def test_custom_values(self):
        limits = DRALimits(timeout_seconds=1.5, max_rows=5, max_result_mb=0.5, memory_limit_mb=64, threads=4)
        assert limits.timeout_seconds == 1.5
        assert limits.max_rows == 5
        assert limits.max_result_mb == 0.5
        assert limits.memory_limit_mb == 64
        assert limits.threads == 4

    def test_is_frozen(self):
        limits = DRALimits()
        with pytest.raises(ValidationError):
            limits.max_rows = 1

    @pytest.mark.parametrize(
        "field, value",
        [
            ("timeout_seconds", 0),
            ("timeout_seconds", -1),
            ("max_rows", 0),
            ("max_result_mb", 0),
            ("max_result_mb", -0.1),
            ("memory_limit_mb", 15),
            ("threads", 0),
        ],
    )
    def test_out_of_range_is_rejected(self, field, value):
        with pytest.raises(ValidationError):
            DRALimits(**{field: value})

    @pytest.mark.parametrize(
        "field, value",
        [
            ("max_rows", 1),
            ("memory_limit_mb", 16),
            ("threads", 1),
        ],
    )
    def test_lower_bounds_are_inclusive(self, field, value):
        assert getattr(DRALimits(**{field: value}), field) == value
