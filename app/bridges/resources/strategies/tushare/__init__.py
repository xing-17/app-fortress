from __future__ import annotations

from app.bridges.resources.strategies.tushare.by_tradedate import (
    TushareByTradedate,  # 触发 @StrategyFactory.register 注册
)

__all__ = [
    "TushareByTradedate",
]
