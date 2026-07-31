"""
Bridges Resources Base Module

提供 Bridges 框架的核心基础组件，包括：
- 服务基类（BaseBridgesService）：异步队列式任务管理
- 状态管理（BaseBridgesState, BaseBridgesStatus）：任务状态跟踪
- 注册表（BaseRegistry）：持久化历史记录
- 健康检查（ServiceHealth）：服务运行时状态监控
- 服务协议（ServiceLike）：标准服务接口定义

这些组件构成了 Bridges 服务架构的基础设施层。
"""

from app.bridges.base.registry import BaseRegistry
from app.bridges.base.service import BaseBridgesService
from app.bridges.base.servicehealth import ServiceHealth
from app.bridges.base.servicelike import ServiceLike
from app.bridges.base.state import BaseBridgesState, BaseBridgesStatus

__all__ = [
    "BaseRegistry",
    "BaseBridgesService",
    "BaseBridgesState",
    "BaseBridgesStatus",
    "ServiceHealth",
    "ServiceLike",
]
