from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.bridges.resources.providers.base.provider import BaseProvider
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class BaseStrategy(
    ABC,
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    策略基类。

    定义数据获取策略的抽象接口，用于将单个参数集展开为多个参数集。
    子类须实现 run 方法。

    Example:
        >>> @StrategyFactory.register("tushare", "by_date")
        ... class MyStrategy(BaseStrategy):
        ...     def run(self, provider, params):
        ...         return [{"date": "2024-01-01"}, {"date": "2024-01-02"}]

    """

    def __init__(self):
        self._set_log_prefix("BaseStrategy()")

    @abstractmethod
    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
