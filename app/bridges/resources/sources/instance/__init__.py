"""
数据源实例集合。

此模块负责导入所有具体的 Source 实现，触发装饰器注册。

重要：
    必须在 base.factory 导入之后才能导入此模块，
    因为具体实现类使用了 @SourceFactory.register() 装饰器。

    导入顺序：
    1. base (定义 SourceFactory)
    2. instance (触发装饰器注册，将具体类注册到工厂)
"""

# 导入所有 instance 子包以触发装饰器注册
# 必须在 SourceFactory 定义之后导入
from app.bridges.resources.sources.instance import (
    tushare,  # noqa: F401 - 副作用导入，触发装饰器
)

# 可选：导出具体类以方便外部使用
from app.bridges.resources.sources.instance.tushare import (
    TushareSource,
    TushareSourceSetting,
)

__all__ = [
    "TushareSource",
    "TushareSourceSetting",
]
