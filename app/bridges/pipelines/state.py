from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from app.bridges.sources.state import SourceStatus
from app.common.plugin import TimePlugin

if TYPE_CHECKING:
    from app.bridges.sources.node import SourceNode


class PipeStatus(str, Enum):
    """
    Pipe 执行状态枚举。

    执行前状态：
        PENDING: 待执行
        RUNNING: 执行中

    执行后状态：
        DONE: 全部成功完成
        PARTIAL: 部分成功（有成功也有失败）
        FAILED: 全部失败
        CANCELED: 已取消
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
class PipeState(TimePlugin):
    """
    Pipe 状态信息

    Attributes:
        status (PipeStatus): 当前状态
        started_at (datetime | None): 开始时间
        finished_at (datetime | None): 结束时间
        total (int): 总节点数
        success (int): 成功节点数
        failed (int): 失败节点数
        running (int): 运行中节点数
        pending (int): 待运行节点数
        canceled (int): 已取消节点数

    Methods:
        start(): 标记开始运行
        cancel(): 标记取消运行
        update(source_nodes): 更新状态统计
        finish(source_nodes): 标记完成运行并更新状态统计
        duration_seconds: 计算运行时长（秒）
        succeeded: 判断是否成功完成
        start_at_repr: 获取开始时间的 ISO 格式字符串
        finish_at_repr: 获取结束时间的 ISO 格式字符串
        export(): 导出状态为字典
        describe(): 导出状态为格式化 JSON 字符串

    Example:
        >>> state = PipeState()
        >>> state.start()
        >>> state.finish(source_nodes)
        >>> print(state.export())
        >>> print(state.describe())

    """

    status: PipeStatus = PipeStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total: int = 0
    success: int = 0
    failed: int = 0
    running: int = 0
    pending: int = 0
    canceled: int = 0

    def start(self) -> None:
        self.status = PipeStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def cancel(self) -> None:
        self.status = PipeStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def update(
        self,
        source_nodes: list[SourceNode],
    ) -> None:
        states = [n.state for n in source_nodes]
        self.total = len(states)
        self.pending = sum(1 for s in states if s.status == SourceStatus.PENDING)
        self.success = sum(1 for s in states if s.status == SourceStatus.SUCCESS)
        self.failed = sum(1 for s in states if s.status == SourceStatus.FAILED)
        self.running = sum(1 for s in states if s.status == SourceStatus.RUNNING)
        self.canceled = sum(1 for s in states if s.status == SourceStatus.CANCELED)

    def finish(
        self,
        source_nodes: list[SourceNode],
    ) -> None:
        self.update(source_nodes)
        self.finished_at = self._get_current_datetime()
        if self.success > 0 and self.failed == 0:
            self.status = PipeStatus.DONE
        elif self.success > 0 and self.failed > 0:
            self.status = PipeStatus.PARTIAL
        elif self.failed > 0:
            self.status = PipeStatus.FAILED
        else:
            if self.total != 0:  # 全部被取消
                self.status = PipeStatus.CANCELED
            else:  # 无节点
                self.status = PipeStatus.DONE

    # ── 只读属性 ──────────────────────────────────────────────
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def succeeded(self) -> bool:
        return self.status == PipeStatus.DONE

    @property
    def start_at_repr(self) -> str | None:
        if self.started_at:
            return self.started_at.isoformat()
        return None

    @property
    def finish_at_repr(self) -> str | None:
        if self.finished_at:
            return self.finished_at.isoformat()
        return None

    def export(self) -> dict:
        return {
            "status": self.status.value,
            "started_at": self.start_at_repr,
            "finished_at": self.finish_at_repr,
            "duration_seconds": self.duration_seconds,
            "total": self.total,
            "pending": self.pending,
            "success": self.success,
            "failed": self.failed,
            "running": self.running,
            "canceled": self.canceled,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
