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
    type: str = "base_bridges_state"
    status: BaseBridgesStatus = BaseBridgesStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def _is_cancelled(self) -> bool:
        return self.status == BaseBridgesStatus.CANCELED

    def cancel(self) -> None:
        self.status = BaseBridgesStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def fail(self) -> None:
        self.status = BaseBridgesStatus.FAILED
        self.finished_at = self._get_current_datetime()

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
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
