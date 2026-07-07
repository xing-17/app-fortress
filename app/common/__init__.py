"""
app.common - 通用基础设施模块

提供应用级通用能力，包括配置管理、日志系统、上下文基类和可混入插件。

## 模块组成

### context - 上下文基类
提供带自动时间戳和序列化能力的基础上下文类。

### core - 核心配置与日志
- CoreSetting: 应用配置聚合器，从 YAML 文件加载所有配置
- GlobalSetting: 全局单例配置对象
- GlobalLogGroup: 全局日志组
- GlobalLogStream: 全局日志流

### plugin - 可混入插件
- TimePlugin: 时区感知的时间工具
- LogPlugin: 结构化日志能力
- StopwatchPlugin: 线程安全计时器

### setting - 配置模型
- SystemSetting: 系统运行时配置
- CentreSetting: 中心节点配置
- ConnectionsSetting: 连接配置（OSS等）
- BridgesSetting: 提供者配置（Tushare等）

## 快速开始

```python
from app.common import GlobalSetting, LogPlugin, TimePlugin

# 1. 使用全局配置
print(GlobalSetting.system.name)
print(GlobalSetting.system.timezone)

# 2. 使用混入插件
class MyService(LogPlugin, TimePlugin):
    def run(self):
        self.info("Service started")
        current_time = self._get_current_datetime()
        self.info(f"Current time: {current_time}")

# 3. 使用上下文基类
from app.common import BaseContext

class TaskContext(BaseContext):
    task_id: str
    status: str

ctx = TaskContext(task_id="task-001", status="running")
print(ctx.export())  # 自动包含 created_at 和 category
```

## 设计特点

- **类型安全**: 完整的类型注解，支持 mypy 静态检查
- **测试完善**: 283 个单元测试，100% 覆盖核心功能
- **插件化**: 通过混入方式灵活组合功能
- **配置驱动**: 所有配置从 YAML 文件加载，支持运行时刷新
- **线程安全**: 关键组件（如 StopwatchPlugin）提供线程安全保证
- **安全性**: 敏感信息自动脱敏导出

"""

# ── Context ───────────────────────────────────────────────────────────────────
from app.common.context.base import BaseContext

# ── Core ──────────────────────────────────────────────────────────────────────
from app.common.core.loggroup import GlobalLogGroup, GlobalLogGroupFactory
from app.common.core.logstream import GlobalLogStream, GlobalLogStreamFactory
from app.common.core.setting import CoreSetting, GlobalSetting

# ── Plugin ────────────────────────────────────────────────────────────────────
from app.common.plugin.log import LogPlugin
from app.common.plugin.stopwatch import StopwatchPlugin
from app.common.plugin.time import TimePlugin

# ── Setting ───────────────────────────────────────────────────────────────────
from app.common.setting.bridges import (
    BridgesSetting,
    ProviderSetting,
    TushareProviderSetting,
)
from app.common.setting.centre import CentreSetting
from app.common.setting.connections import (
    ConnectionSetting,
    ConnectionsSetting,
    OssConnectionSetting,
)
from app.common.setting.system import SystemSetting

__all__ = [
    # Context
    "BaseContext",
    # Core
    "CoreSetting",
    "GlobalSetting",
    "GlobalLogGroup",
    "GlobalLogGroupFactory",
    "GlobalLogStream",
    "GlobalLogStreamFactory",
    # Plugin
    "TimePlugin",
    "LogPlugin",
    "StopwatchPlugin",
    # Setting
    "SystemSetting",
    "CentreSetting",
    "ConnectionsSetting",
    "ConnectionSetting",
    "OssConnectionSetting",
    "BridgesSetting",
    "ProviderSetting",
    "TushareProviderSetting",
]
