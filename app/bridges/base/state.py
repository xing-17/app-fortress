from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.common.plugin import TimePlugin


class BaseBridgesStatus(str, Enum):
    """
    BaseBridgesStatus 的状态枚举。

    Attributes:
        PENDING:  请求已创建，但尚未开始执行。
        RUNNING:  请求正在执行中。
        DONE:     请求已成功完成，所有 PipeNode 均为 DONE。
        PARTIAL:  请求部分完成，至少有一个 PipeNode 为 PARTIAL。
        FAILED:   请求失败，所有 PipeNode 均为 FAILED。
        CANCELED: 请求被取消。
    Methods:
        value: 返回状态的字符串表示。

    """

    # Before run
    PENDING = "PENDING"
    RUNNING = "RUNNING"

    # After run
    DONE = "DONE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass
class BaseBridgesState(TimePlugin):
    """
    Bridges 任务状态基类。

    用于跟踪和管理 Bridges 服务中任务请求的执行状态，包括状态转换、时间戳、
    以及各状态计数器等信息。

    Attributes:
        type (str): 状态类型标识，默认为 "base_bridges_state"。
        status (BaseBridgesStatus): 当前状态，初始为 PENDING。
        started_at (datetime | None): 任务开始时间。
        finished_at (datetime | None): 任务完成时间。
        total (int): 总任务数量。
        pending (int): 待处理任务数。
        running (int): 运行中任务数。
        canceled (int): 已取消任务数。
        done (int): 已完成任务数。
        partial (int): 部分完成任务数。
        failed (int): 失败任务数。
        error (str | None): 错误信息（若有）。

    Properties:
        duration_seconds (float | None): 任务持续时间（秒），仅在任务已开始且已完成时计算。
        started_at_repr (str | None): started_at 的 ISO 格式字符串表示。
        finished_at_repr (str | None): finished_at 的 ISO 格式字符串表示。

    Methods:
        cancel() -> None: 将状态标记为 CANCELED，并设置 finished_at 为当前时间。
        fail(error: str | None = None) -> None: 将状态标记为 FAILED，设置 finished_at 和可选的错误信息。
        export() -> dict[str, Any]: 导出状态为字典格式。
        describe() -> str: 返回状态的 JSON 字符串表示。

    Private Methods:
        _is_cancelled() -> bool: 检查当前状态是否为 CANCELED。

    Example:
        >>> state = BaseBridgesState()
        >>> state.started_at = datetime.now()
        >>> state.status = BaseBridgesStatus.RUNNING
        >>> # ... 执行任务 ...
        >>> state.cancel()  # 或 state.fail("error message")
        >>> print(state.duration_seconds)
        >>> print(state.export())
    """

    type: str = "base_bridges_state"
    status: BaseBridgesStatus = BaseBridgesStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total: int = 0
    pending: int = 0
    running: int = 0
    canceled: int = 0
    done: int = 0
    partial: int = 0
    failed: int = 0
    error: str | None = None

    def _is_cancelled(self) -> bool:
        return self.status == BaseBridgesStatus.CANCELED

    def cancel(self) -> None:
        self.status = BaseBridgesStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def fail(
        self,
        error: str | None = None,
    ) -> None:
        self.status = BaseBridgesStatus.FAILED
        self.finished_at = self._get_current_datetime()
        if error:
            self.error = error

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def started_at_repr(self) -> str | None:
        return self.started_at.isoformat() if self.started_at else None

    @property
    def finished_at_repr(self) -> str | None:
        return self.finished_at.isoformat() if self.finished_at else None

    def export(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "status": self.status.value,
            "started_at": self.started_at_repr,
            "finished_at": self.finished_at_repr,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            # 子类自己选择是否导出 total 等, 不做实现
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
