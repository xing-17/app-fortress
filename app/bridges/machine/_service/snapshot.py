from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class MachineSnapshot(BaseContext):
    """
    系统资源快照数据模型。

    封装单次系统资源采样的所有指标数据，包括 CPU、内存、磁盘、网络和进程信息。
    继承自 BaseContext，自动生成唯一 ID 和时间戳。

    Attributes:
        cpu_percent (float): CPU 使用率（百分比，0-100）。
        mem_percent (float): 内存使用率（百分比，0-100）。
        mem_used_mb (float): 已使用内存（MB）。
        mem_total_mb (float): 总内存（MB）。
        swap_percent (float): 交换分区使用率（百分比，0-100）。
        disk_percent (float): 磁盘使用率（百分比，0-100）。
        disk_used_mb (float): 已使用磁盘空间（MB）。
        disk_total_mb (float): 总磁盘空间（MB）。
        proc_mem_mb (float | None): 当前进程已使用内存（MB），采集失败时为 None。
        proc_mem_percent (float | None): 当前进程内存使用率（百分比），采集失败时为 None。
        proc_cpu_percent (float | None): 当前进程 CPU 使用率（百分比），采集失败时为 None。
        proc_workers (int | None): 当前进程线程数，采集失败时为 None。
        net_sent_mb (float | None): 网络发送流量（MB，累计值），采集失败时为 None。
        net_recv_mb (float | None): 网络接收流量（MB，累计值），采集失败时为 None。

    Properties:
        id (str): 唯一标识符（自动生成，格式: macs-[16 位随机字符]）。
        created_at (datetime): 创建时间戳（采样时间）。

    Methods:
        export() -> dict:
            导出快照数据为字典，包含所有字段和 Unix 时间戳。
            在基类 export() 的基础上添加 'timestamp' 字段（created_at 的 Unix 时间戳）。

    Example:
        >>> snapshot = MachineSnapshot(
        ...     cpu_percent=45.2,
        ...     mem_percent=68.5,
        ...     mem_used_mb=8192,
        ...     mem_total_mb=12288,
        ...     swap_percent=10.0,
        ...     disk_percent=75.3,
        ...     disk_used_mb=512000,
        ...     disk_total_mb=680000,
        ...     proc_mem_mb=256,
        ...     proc_mem_percent=2.08,
        ...     proc_cpu_percent=12.5,
        ...     proc_workers=8,
        ...     net_sent_mb=1024,
        ...     net_recv_mb=2048,
        ... )
        >>> data = snapshot.export()
        >>> print(f"CPU: {data['cpu_percent']}%")
        >>> print(f"Memory: {data['mem_used_mb']} / {data['mem_total_mb']} MB")
        >>> print(f"Timestamp: {data['timestamp']}")
    """

    id_prefix: ClassVar[str] = "macs-"
    id_length: ClassVar[int] = 16
    cpu_percent: float = Field(
        ...,
        description="CPU 使用率(百分比)",
    )
    mem_percent: float = Field(
        ...,
        description="内存使用率(百分比)",
    )
    mem_used_mb: float = Field(
        ...,
        description="已使用内存(MB)",
    )
    mem_total_mb: float = Field(
        ...,
        description="总内存(MB)",
    )
    swap_percent: float = Field(
        ...,
        description="交换分区使用率(百分比)",
    )
    disk_percent: float = Field(
        ...,
        description="磁盘使用率(百分比)",
    )
    disk_used_mb: float = Field(
        ...,
        description="已使用磁盘空间(MB)",
    )
    disk_total_mb: float = Field(
        ...,
        description="总磁盘空间(MB)",
    )
    proc_mem_mb: float | None = Field(
        None,
        description="当前进程已使用内存(MB)",
    )
    proc_mem_percent: float | None = Field(
        None,
        description="当前进程内存使用率(百分比)",
    )
    proc_cpu_percent: float | None = Field(
        None,
        description="当前进程 CPU 使用率(百分比)",
    )
    proc_workers: int | None = Field(
        None,
        description="当前进程线程数",
    )
    net_sent_mb: float | None = Field(
        None,
        description="网络发送流量(MB)",
    )
    net_recv_mb: float | None = Field(
        None,
        description="网络接收流量(MB)",
    )
    
    @property
    def timestamp(self) -> float | None:
        if self.created_at:
            return self.created_at.timestamp()
        return None

    def export(self) -> dict:
        result: dict = super().export()
        result["timestamp"] = self.timestamp
        return result
