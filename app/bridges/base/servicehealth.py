from __future__ import annotations

from time import monotonic
from typing import Any, ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class ServiceHealth(BaseContext):
    """
    服务健康状态数据模型。

    用于封装和导出服务（如 BaseBridgesService）的运行时健康状态信息，
    包括工作线程状态、队列状态、最后活跃时间等关键指标。

    Attributes:
        service (str): 服务名称标识。
        worker_name (str | None): 工作线程名称。
        worker_alive (bool | None): 工作线程是否存活。
        worker_daemon (bool | None): 工作线程是否为守护线程。
        worker_ident (int | None): 工作线程标识符（Python 线程 ID）。
        worker_native_id (int | None): 工作线程原生标识符（操作系统线程 ID）。
        worker_count (int | None): 当前活跃的工作线程总数。
        queue_size (int | None): 任务队列当前大小。
        queue_limit (int | None): 任务队列容量限制。
        queue_full (bool | None): 任务队列是否已满。
        last_active_time (float | None): 最后活跃时间戳（monotonic 时间，自启动以来的秒数）。

    Properties:
        queue_usage (float): 队列使用率（0.0-1.0），计算为 queue_size / queue_limit。
        idle_seconds (float | None): 自最后活跃时间以来的空闲秒数。

    Methods:
        export() -> dict[str, Any]: 导出完整的健康状态为字典，包含工作线程和队列的详细信息。

    Example:
        >>> health = service.health()
        >>> print(f"Service: {health.service}")
        >>> print(f"Queue usage: {health.queue_usage:.2%}")
        >>> print(f"Idle for: {health.idle_seconds}s")
        >>> print(health.export())
    """

    id_prefix: ClassVar[str] = "svch"
    id_length: ClassVar[int] = 10

    service: str = Field(
        ...,
        description="服务名称",
    )
    worker_name: str | None = Field(
        None,
        description="服务的工作线程名称",
    )
    worker_alive: bool | None = Field(
        None,
        description="服务的工作线程是否存活",
    )
    worker_daemon: bool | None = Field(
        None,
        description="服务的工作线程是否为守护线程",
    )
    worker_ident: int | None = Field(
        None,
        description="服务的工作线程标识符",
    )
    worker_native_id: int | None = Field(
        None,
        description="服务的工作线程原生标识符",
    )
    worker_count: int | None = Field(
        None,
        description="服务的工作线程数量",
    )
    queue_size: int | None = Field(
        None,
        description="服务的任务队列大小",
    )
    queue_limit: int | None = Field(
        None,
        description="服务的任务队列限制",
    )
    queue_full: bool | None = Field(
        None,
        description="服务的任务队列是否已满",
    )
    last_active_time: float | None = Field(
        None,
        description="服务的最后活跃时间（自启动以来的秒数）",
    )

    @property
    def queue_usage(self) -> float:
        if not self.queue_limit:
            return 0.0
        return round(self.queue_size / self.queue_limit, 4)

    @property
    def idle_seconds(self) -> float | None:
        if self.last_active_time is None:
            return None
        current_time = monotonic()
        return round(current_time - self.last_active_time, 2)

    def export(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "last_active_time": self.last_active_time,
            "idle_seconds": self.idle_seconds,
            "worker": {
                "name": self.worker_name,
                "alive": self.worker_alive,
                "daemon": self.worker_daemon,
                "ident": self.worker_ident,
                "native_id": self.worker_native_id,
                "count": self.worker_count,
            },
            "queue": {
                "size": self.queue_size,
                "limit": self.queue_limit,
                "full": self.queue_full,
                "usage": self.queue_usage,
            },
        }
