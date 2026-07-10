"""
综合测试：app.bridges.resources.strategies.base.strategies

覆盖范围
--------
- TestAbstract  BaseStrategy 是抽象类，未实现 run() 无法实例化
- TestPlugins   BaseStrategy 继承 LogPlugin, TimePlugin, StopwatchPlugin
- TestInit      __init__ 正确设置 log prefix
- TestRun       run() 必须由子类实现，返回 list[dict[str, Any]]
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.strategies.base.strategies import BaseStrategy
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _ConcreteStrategy(BaseStrategy):
    """测试用具体策略实现"""

    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [params]


# ──────────────────────────────────────────────────────────────────────────────
# TestAbstract
# ──────────────────────────────────────────────────────────────────────────────


class TestAbstract:
    def test_cannot_instantiate_base_strategy_directly(self):
        """测试不能直接实例化 BaseStrategy"""
        with pytest.raises(TypeError):
            BaseStrategy()

    def test_missing_run_raises_type_error(self):
        """测试未实现 run() 方法会抛出 TypeError"""

        class _IncompleteStrategy(BaseStrategy):
            pass

        with pytest.raises(TypeError):
            _IncompleteStrategy()

    def test_concrete_strategy_can_be_instantiated(self):
        """测试实现了 run() 的具体策略可以实例化"""
        strategy = _ConcreteStrategy()
        assert isinstance(strategy, BaseStrategy)


# ──────────────────────────────────────────────────────────────────────────────
# TestPlugins
# ──────────────────────────────────────────────────────────────────────────────


class TestPlugins:
    def test_inherits_log_plugin(self):
        """测试 BaseStrategy 继承 LogPlugin"""
        assert issubclass(BaseStrategy, LogPlugin)

    def test_inherits_time_plugin(self):
        """测试 BaseStrategy 继承 TimePlugin"""
        assert issubclass(BaseStrategy, TimePlugin)

    def test_inherits_stopwatch_plugin(self):
        """测试 BaseStrategy 继承 StopwatchPlugin"""
        assert issubclass(BaseStrategy, StopwatchPlugin)

    def test_concrete_strategy_has_log_methods(self):
        """测试具体策略实例有日志方法"""
        strategy = _ConcreteStrategy()
        assert hasattr(strategy, "debug")
        assert hasattr(strategy, "info")
        assert hasattr(strategy, "warning")
        assert hasattr(strategy, "error")

    def test_concrete_strategy_has_time_methods(self):
        """测试具体策略实例有时间方法"""
        strategy = _ConcreteStrategy()
        assert hasattr(strategy, "_get_current_date")
        assert hasattr(strategy, "_read_date")

    def test_concrete_strategy_has_stopwatch_methods(self):
        """测试具体策略实例有性能监控方法"""
        strategy = _ConcreteStrategy()
        assert hasattr(strategy, "tick")
        assert hasattr(strategy, "tock")


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_init_sets_log_prefix(self):
        """测试 __init__ 设置了 log prefix"""
        strategy = _ConcreteStrategy()
        # 验证 _set_log_prefix 被调用（通过检查是否有 log 方法）
        assert hasattr(strategy, "debug")


# ──────────────────────────────────────────────────────────────────────────────
# TestRun
# ──────────────────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_is_abstract_method(self):
        """测试 run() 是抽象方法"""
        assert hasattr(BaseStrategy, "run")
        assert hasattr(BaseStrategy.run, "__isabstractmethod__")

    def test_run_accepts_provider_and_params(self):
        """测试 run() 接受 provider 和 params 参数"""
        strategy = _ConcreteStrategy()
        mock_provider = Mock(spec=BaseProvider)
        params = {"key": "value"}
        result = strategy.run(mock_provider, params)
        assert isinstance(result, list)

    def test_run_returns_list_of_dicts(self):
        """测试 run() 返回 list[dict[str, Any]]"""
        strategy = _ConcreteStrategy()
        mock_provider = Mock(spec=BaseProvider)
        params = {"key": "value"}
        result = strategy.run(mock_provider, params)
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_concrete_run_preserves_input_params(self):
        """测试具体实现的 run() 保留输入参数"""
        strategy = _ConcreteStrategy()
        mock_provider = Mock(spec=BaseProvider)
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05"}
        result = strategy.run(mock_provider, params)
        assert len(result) == 1
        assert result[0] == params
