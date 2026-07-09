"""
数据源模块。

提供基于 YAML 配置的数据源定义、工厂管理和自动发现机制。

架构：
    - base/: 基础抽象层（BaseSource, SourceFactory, BaseSourceSetting）
    - instance/: 具体实现层（TushareSource, ...）
    - items/: YAML 配置文件

导入顺序说明：
    由于使用了装饰器注册模式，导入顺序至关重要：
    1. 先导入 base（定义 SourceFactory 和基类）
    2. 再导入 instance（触发 @SourceFactory.register 装饰器）
    3. 此时工厂已包含所有注册的 Source 类

使用示例：
    >>> from app.bridges.resources.sources import SourceFactory
    >>> # 从 YAML 加载单个 source
    >>> source = SourceFactory.from_yaml("items/tushare/tushare_stock_capflow.yaml")
    >>> # 批量加载所有 source
    >>> sources = SourceFactory.bootstrap()
    >>> print(sources.keys())
"""

# 步骤 1: 导入基础组件（定义工厂和抽象类）
# 步骤 2: 导入所有 instance 以触发装饰器注册
# 必须在 SourceFactory 导入之后，这样装饰器执行时工厂已经存在
from app.bridges.resources.sources import (
    instance,  # noqa: F401 - 副作用导入，触发所有 Source 子类的注册
)
from app.bridges.resources.sources.base import (
    BaseSource,
    BaseSourceSetting,
    SourceFactory,
)

# 步骤 3: 导出具体实现类（可选，方便外部使用）
from app.bridges.resources.sources.instance import (
    TushareSource,
    TushareSourceSetting,
)

__all__ = [
    # 基础组件
    "BaseSource",
    "BaseSourceSetting",
    "SourceFactory",
    # Tushare 实现
    "TushareSource",
    "TushareSourceSetting",
]
