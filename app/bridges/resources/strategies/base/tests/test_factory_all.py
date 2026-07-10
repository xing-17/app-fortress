"""
综合测试：app.bridges.resources.strategies.base.factory

覆盖范围
--------
- TestRegister  register() 写入注册表，重复注册抛 ValueError，返回原类
- TestCreate    create() 根据 key 创建策略实例，未找到抛 KeyError
- TestRegistry  _registry 正确存储策略类
"""

from __future__ import annotations

from typing import Any

import pytest

from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _MockStrategy(BaseStrategy):
    """测试用 mock 策略"""

    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [params]


class _AnotherMockStrategy(BaseStrategy):
    """测试用另一个 mock 策略"""

    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [params, params]


# ──────────────────────────────────────────────────────────────────────────────
# TestRegister
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_stores_class_in_registry(self, monkeypatch):
        """测试 register() 将策略类存储到注册表"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        assert ("mock", "test") in StrategyFactory._registry

    def test_register_maps_key_to_correct_class(self, monkeypatch):
        """测试 register() 正确映射 key 到策略类"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        assert StrategyFactory._registry[("mock", "test")] is _MockStrategy

    def test_register_returns_class_unchanged(self, monkeypatch):
        """测试 register() 返回原类（不修改）"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        result = StrategyFactory.register("mock", "test")(_MockStrategy)
        assert result is _MockStrategy

    def test_register_duplicate_raises_value_error(self, monkeypatch):
        """测试重复注册同一 key 会抛出 ValueError"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        with pytest.raises(ValueError, match="already registered"):
            StrategyFactory.register("mock", "test")(_AnotherMockStrategy)

    def test_register_multiple_different_keys(self, monkeypatch):
        """测试注册多个不同 key 的策略"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test1")(_MockStrategy)
        StrategyFactory.register("mock", "test2")(_AnotherMockStrategy)
        assert ("mock", "test1") in StrategyFactory._registry
        assert ("mock", "test2") in StrategyFactory._registry

    def test_register_different_providers_same_strategy_name(self, monkeypatch):
        """测试不同 provider 可以有同名策略"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("tushare", "by_date")(_MockStrategy)
        StrategyFactory.register("akshare", "by_date")(_AnotherMockStrategy)
        assert ("tushare", "by_date") in StrategyFactory._registry
        assert ("akshare", "by_date") in StrategyFactory._registry

    def test_register_as_decorator(self, monkeypatch):
        """测试 register() 作为装饰器使用"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})

        @StrategyFactory.register("mock", "decorated")
        class _DecoratedStrategy(BaseStrategy):
            def run(self, provider, params):
                return []

        assert ("mock", "decorated") in StrategyFactory._registry
        assert StrategyFactory._registry[("mock", "decorated")] is _DecoratedStrategy


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_returns_strategy_instance(self, monkeypatch):
        """测试 create() 返回策略实例"""
        monkeypatch.setattr(StrategyFactory, "_registry", {("mock", "test"): _MockStrategy})
        strategy = StrategyFactory.create(("mock", "test"))
        assert isinstance(strategy, _MockStrategy)

    def test_create_returns_base_strategy_instance(self, monkeypatch):
        """测试 create() 返回的实例是 BaseStrategy 的子类"""
        monkeypatch.setattr(StrategyFactory, "_registry", {("mock", "test"): _MockStrategy})
        strategy = StrategyFactory.create(("mock", "test"))
        assert isinstance(strategy, BaseStrategy)

    def test_create_with_unknown_key_raises_key_error(self, monkeypatch):
        """测试 create() 使用未注册的 key 会抛出 KeyError"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        with pytest.raises(KeyError, match="not found"):
            StrategyFactory.create(("unknown", "strategy"))

    def test_create_new_instance_each_time(self, monkeypatch):
        """测试 create() 每次返回新实例"""
        monkeypatch.setattr(StrategyFactory, "_registry", {("mock", "test"): _MockStrategy})
        strategy1 = StrategyFactory.create(("mock", "test"))
        strategy2 = StrategyFactory.create(("mock", "test"))
        assert strategy1 is not strategy2

    def test_create_with_tuple_key(self, monkeypatch):
        """测试 create() 接受 tuple key"""
        monkeypatch.setattr(StrategyFactory, "_registry", {("tushare", "by_date"): _MockStrategy})
        strategy = StrategyFactory.create(("tushare", "by_date"))
        assert isinstance(strategy, _MockStrategy)


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistry
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_registry_is_class_variable(self):
        """测试 _registry 是类变量"""
        assert hasattr(StrategyFactory, "_registry")
        assert isinstance(StrategyFactory._registry, dict)

    def test_registry_key_is_tuple(self, monkeypatch):
        """测试 _registry 的 key 是 tuple"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        keys = list(StrategyFactory._registry.keys())
        assert len(keys) == 1
        assert isinstance(keys[0], tuple)
        assert len(keys[0]) == 2

    def test_registry_value_is_class(self, monkeypatch):
        """测试 _registry 的 value 是类"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        values = list(StrategyFactory._registry.values())
        assert len(values) == 1
        assert values[0] is _MockStrategy

    def test_registry_shared_across_instances(self, monkeypatch):
        """测试 _registry 在所有实例间共享"""
        monkeypatch.setattr(StrategyFactory, "_registry", {})
        StrategyFactory.register("mock", "test")(_MockStrategy)
        # 验证注册表在类级别
        assert ("mock", "test") in StrategyFactory._registry
