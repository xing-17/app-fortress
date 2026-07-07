"""
综合测试：app.bridges.resources.accessory.jitter

覆盖范围
--------
- TestResolveSeconds  _resolve_seconds() None 直通、float/int 转换、负值与非法值抛异常
- TestIsEnabled       is_enabled 在各种参数组合下的值
- TestValidation      min >= max 时构造抛 ValueError
- TestJit             jit() 在 enabled/disabled 两种状态下的行为
- TestExport          export() 包含必要键且值与实例属性一致
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.bridges.resources.accessory.jitter import Jitter

# ──────────────────────────────────────────────────────────────────────────────
# TestResolveSeconds
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveSeconds:
    def test_none_returns_none(self):
        j = Jitter()
        assert j._resolve_seconds(None) is None

    def test_int_is_converted_to_float(self):
        j = Jitter()
        result = j._resolve_seconds(2)
        assert isinstance(result, float)
        assert result == 2.0

    def test_float_is_stored_as_float(self):
        j = Jitter()
        result = j._resolve_seconds(1.5)
        assert result == 1.5

    def test_zero_is_allowed(self):
        j = Jitter()
        result = j._resolve_seconds(0)
        assert result == 0.0

    def test_negative_value_raises(self):
        j = Jitter()
        with pytest.raises(ValueError, match="negative"):
            j._resolve_seconds(-1.0)

    def test_non_numeric_string_raises(self):
        j = Jitter()
        with pytest.raises(ValueError):
            j._resolve_seconds("fast")


# ──────────────────────────────────────────────────────────────────────────────
# TestIsEnabled
# ──────────────────────────────────────────────────────────────────────────────


class TestIsEnabled:
    def test_both_none_is_disabled(self):
        j = Jitter()
        assert j.is_enabled is False

    def test_only_min_raises(self):
        with pytest.raises(ValueError):
            Jitter(min_seconds=0.5)

    def test_only_max_raises(self):
        with pytest.raises(ValueError):
            Jitter(max_seconds=1.5)

    def test_both_valid_is_enabled(self):
        j = Jitter(min_seconds=0.5, max_seconds=1.5)
        assert j.is_enabled is True

    def test_min_zero_with_valid_max_is_enabled(self):
        j = Jitter(min_seconds=0.0, max_seconds=1.0)
        assert j.is_enabled is True


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_min_equal_to_max_raises(self):
        with pytest.raises(ValueError, match="min_seconds must be < max_seconds"):
            Jitter(min_seconds=1.0, max_seconds=1.0)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_seconds must be < max_seconds"):
            Jitter(min_seconds=2.0, max_seconds=1.0)

    def test_min_none_max_set_raises(self):
        with pytest.raises(ValueError):
            Jitter(max_seconds=1.0)

    def test_min_set_max_none_raises(self):
        with pytest.raises(ValueError):
            Jitter(min_seconds=0.5)


# ──────────────────────────────────────────────────────────────────────────────
# TestJit
# ──────────────────────────────────────────────────────────────────────────────


class TestJit:
    def test_jit_does_not_sleep_when_disabled(self):
        j = Jitter()
        with patch("time.sleep") as mock_sleep:
            j.jit()
            mock_sleep.assert_not_called()

    def test_jit_calls_sleep_when_enabled(self):
        j = Jitter(min_seconds=0.5, max_seconds=1.5)
        with patch("app.bridges.resources.accessory.jitter.time.sleep") as mock_sleep:
            j.jit()
            mock_sleep.assert_called_once()

    def test_jit_sleep_value_within_range(self):
        j = Jitter(min_seconds=0.5, max_seconds=1.5)
        captured: list[float] = []
        with patch("app.bridges.resources.accessory.jitter.time.sleep", side_effect=captured.append):
            j.jit()
        assert len(captured) == 1
        assert 0.5 <= captured[0] <= 1.5

    def test_jit_sleep_value_is_rounded_to_3_decimals(self):
        j = Jitter(min_seconds=0.5, max_seconds=1.5)
        captured: list[float] = []
        with patch("app.bridges.resources.accessory.jitter.time.sleep", side_effect=captured.append):
            j.jit()
        assert captured[0] == round(captured[0], 3)


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_required_keys(self):
        j = Jitter()
        result = j.export()
        assert {"min_seconds", "max_seconds", "is_enabled"}.issubset(result)

    def test_export_includes_base_klass_key(self):
        j = Jitter()
        assert "klass" in j.export()

    def test_export_values_match_attributes(self):
        j = Jitter(min_seconds=0.5, max_seconds=1.5)
        result = j.export()
        assert result["min_seconds"] == j.min_seconds
        assert result["max_seconds"] == j.max_seconds
        assert result["is_enabled"] == j.is_enabled

    def test_export_disabled_jitter_has_none_values(self):
        j = Jitter()
        result = j.export()
        assert result["min_seconds"] is None
        assert result["max_seconds"] is None
        assert result["is_enabled"] is False
