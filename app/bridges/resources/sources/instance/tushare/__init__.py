"""
Tushare 数据源实例。

提供 Tushare 特定的 Source 和 Setting 实现。

注意：
    导入此模块会触发 @SourceFactory.register("tushare") 装饰器，
    将 TushareSource 注册到全局工厂。请确保在导入此模块前已导入 base.factory。
"""

from app.bridges.resources.sources.instance.tushare.setting import TushareSourceSetting
from app.bridges.resources.sources.instance.tushare.source import TushareSource

__all__ = [
    "TushareSourceSetting",
    "TushareSource",
]
