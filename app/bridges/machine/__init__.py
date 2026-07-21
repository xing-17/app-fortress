"""
Bridges Machine Module

提供系统资源监控和指标采集服务，包括：
- 机器服务（MachineService）：后台定时采样系统指标
- 快照模型（MachineSnapshot）：系统资源快照数据结构

核心功能：
- 定时采集 CPU、内存、磁盘、网络、进程等系统指标
- 循环缓冲区保存历史采样数据
- 支持实时查询和历史数据回溯
- 线程安全的并发访问

使用场景：
- 系统健康监控
- 性能分析和诊断
- OOM（内存溢出）问题排查
- 资源使用趋势分析
"""

from app.bridges.machine._service.service import MachineService
from app.bridges.machine._service.snapshot import MachineSnapshot

__all__ = [
    "MachineService",
    "MachineSnapshot",
]
