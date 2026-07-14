from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.common.plugin import TimePlugin


class SourceStatus(str, Enum):
    # Before run
    PENDING = "PENDING"
    RUNNING = "RUNNING"

    # After run
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass
class SourceState(TimePlugin):
    """
    单次 SourceNode 执行状态追踪对象。

    记录 SourceNode 执行过程中的状态变化、时间信息、数据行数和错误信息。
    支持状态转换：PENDING → RUNNING → (SUCCESS | FAILED | CANCELED)

    状态转换流程：
        PENDING (初始) → RUNNING (开始) → SUCCESS (完成)
                                       → FAILED (失败)
                                       → CANCELED (取消)

    Attributes:
        status (SourceStatus): 当前执行状态，默认 PENDING
            - PENDING: 待执行
            - RUNNING: 执行中
            - SUCCESS: 执行成功
            - FAILED: 执行失败
            - CANCELED: 已取消

        started_at (datetime | None): 开始执行时间，调用 start() 时设置
        finished_at (datetime | None): 结束执行时间，调用 finish/fail/cancel 时设置
        rows (int): 成功抓取的数据行数，默认 0
        error (str | None): 错误信息，仅在 FAILED 状态时有值

    Properties:
        duration_seconds (float | None): 执行时长（秒），需要 started_at 和 finished_at 都存在
        succeeded (bool): 是否执行成功，等价于 status == SUCCESS
        start_at_repr (str | None): 开始时间的 ISO 格式字符串表示
        finish_at_repr (str | None): 结束时间的 ISO 格式字符串表示

    Methods:
        start() -> None:
            标记开始执行，设置状态为 RUNNING，记录开始时间。

        finish(rows: int = 0) -> None:
            标记执行成功，设置状态为 SUCCESS，记录结束时间和抓取行数。

        fail(error: str) -> None:
            标记执行失败，设置状态为 FAILED，记录结束时间和错误信息。

        cancel() -> None:
            标记执行取消，设置状态为 CANCELED，记录结束时间。

        export() -> dict:
            导出为字典格式，包含所有状态信息。

        describe() -> str:
            返回 JSON 格式的状态信息字符串。

    Example:
        >>> state = SourceState()
        >>> state.status
        <SourceStatus.PENDING: 'PENDING'>

        >>> state.start()
        >>> state.status
        <SourceStatus.RUNNING: 'RUNNING'>

        >>> state.finish(rows=1000)
        >>> state.succeeded
        True
        >>> state.rows
        1000
        >>> state.duration_seconds
        0.123

    """

    status: SourceStatus = SourceStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rows: int = 0
    error: str | None = None

    # ── 状态转换 ──────────────────────────────────────────────
    def start(self) -> None:
        self.status = SourceStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def finish(
        self,
        rows: int = 0,
    ) -> None:
        self.status = SourceStatus.SUCCESS
        self.finished_at = self._get_current_datetime()
        self.rows = rows

    def fail(
        self,
        error: str,
    ) -> None:
        self.status = SourceStatus.FAILED
        self.finished_at = self._get_current_datetime()
        self.error = error

    # ── 只读属性 ──────────────────────────────────────────────
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def succeeded(self) -> bool:
        return self.status == SourceStatus.SUCCESS

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

    def cancel(self) -> None:
        self.status = SourceStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def export(self) -> dict:
        return {
            "status": self.status.value,
            "started_at": self.start_at_repr,
            "finished_at": self.finish_at_repr,
            "duration_seconds": self.duration_seconds,
            "rows": self.rows,
            "error": self.error,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
