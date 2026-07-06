"""
综合测试：app.bridges.accessory.coolant

覆盖范围
--------
- TestResolveInterval  _resolve_interval() None 默认值、float/int 转换、负值与非法值抛异常
- TestRun              run() 在不同 interval 下的行为
- TestContextManager   __enter__ / __exit__ 上下文管理协议
- TestExport           export() 包含必要键且值与实例属性一致
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.bridges.accessory.coolant import Coolant

# ──────────────────────────────────────────────────────────────────────────────
# TestResolveInterval
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveInterval:
    def test_none_returns_default(self):
        c = Coolant()
        assert c.interval == 0.0

    def test_int_is_converted_to_float(self):
        c = Coolant(interval=2)
        assert isinstance(c.interval, float)
        assert c.interval == 2.0

    def test_float_is_stored_as_float(self):
        c = Coolant(interval=1.5)
        assert c.interval == 1.5

    def test_zero_is_allowed(self):
        c = Coolant(interval=0)
        assert c.interval == 0.0

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="must be > 0"):
            Coolant(interval=-1.0)

    def test_non_numeric_value_raises(self):
        with pytest.raises(ValueError):
            Coolant(interval="fast")


# ──────────────────────────────────────────────────────────────────────────────
# TestRun
# ──────────────────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_does_not_sleep_when_interval_zero(self):
        c = Coolant(interval=0.0)
        with patch("time.sleep") as mock_sleep:
            c.run()
            mock_sleep.assert_not_called()

    def test_run_calls_sleep_when_interval_positive(self):
        c = Coolant(interval=1.0)
        with patch("app.bridges.accessory.coolant.time.sleep") as mock_sleep:
            c.run()
            mock_sleep.assert_called_once_with(1.0)

    def test_run_sleep_value_matches_interval(self):
        c = Coolant(interval=2.5)
        captured: list[float] = []
        with patch("app.bridges.accessory.coolant.time.sleep", side_effect=captured.append):
            c.run()
        assert len(captured) == 1
        assert captured[0] == 2.5


# ──────────────────────────────────────────────────────────────────────────────
# TestContextManager
# ──────────────────────────────────────────────────────────────────────────────


class TestContextManager:
    def test_enter_returns_self(self):
        c = Coolant(interval=1.0)
        with c as context:
            assert context is c

    def test_exit_returns_false(self):
        c = Coolant(interval=1.0)
        result = c.__exit__(None, None, None)
        assert result is False

    def test_context_manager_works(self):
        """验证上下文管理器协议可以正常使用"""
        with Coolant(interval=0.1) as c:
            assert isinstance(c, Coolant)


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_interval(self):
        c = Coolant(interval=1.5)
        result = c.export()
        assert "interval" in result

    def test_export_includes_base_klass_key(self):
        c = Coolant()
        assert "klass" in c.export()

    def test_export_values_match_attributes(self):
        c = Coolant(interval=2.5)
        result = c.export()
        assert result["interval"] == c.interval

    def test_export_default_interval_is_zero(self):
        c = Coolant()
        result = c.export()
        assert result["interval"] == 0.0
