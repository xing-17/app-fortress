from __future__ import annotations

from app.bridges.resources.strategies.base.strategies import BaseStrategy


class StrategyFactory:
    """
    策略注册工厂。

    提供基于 (provider_type, strategy_name) 元组的注册机制。

    Methods:
        register(provider_type, strategy_name): 装饰器，注册策略类
        create(key): 根据 key 创建策略实例

    Example:
        >>> @StrategyFactory.register("tushare", "by_tradedate")
        ... class MyStrategy(BaseStrategy): ...
        >>> strategy = StrategyFactory.create(("tushare", "by_tradedate"))

    """

    _registry: dict[tuple[str, str], type[BaseStrategy]] = {}

    @classmethod
    def register(
        cls,
        provider_type: str,
        strategy_name: str,
    ):
        def decorator(klass: type[BaseStrategy]):
            key = (provider_type, strategy_name)
            if key in cls._registry:
                raise ValueError(f"Strategy '{provider_type}.{strategy_name}' already registered.")
            cls._registry[key] = klass
            return klass

        return decorator

    @classmethod
    def create(
        cls,
        key: tuple[str, str],
    ) -> BaseStrategy:
        klass = cls._registry.get(key)
        if klass is None:
            raise KeyError(f"Strategy '{key}' not found.")
        return klass()
