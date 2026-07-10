from __future__ import annotations

# 步骤 1: 导入基础组件（定义工厂和抽象类）
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy

# 步骤 2: 导入所有 instance 以触发装饰器注册
# 必须在 StrategyFactory 导入之后，这样装饰器执行时工厂已经存在
from app.bridges.resources.strategies import (
    tushare,  # noqa: F401 - 副作用导入，触发所有 Strategy 子类的注册
)

__all__ = [
    "BaseStrategy",
    "StrategyFactory",
]
