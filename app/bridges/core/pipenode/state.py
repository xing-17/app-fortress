from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.bridges.resources.base.state import BaseBridgesState, BaseBridgesStatus

# Alias for semantic clarity
PipeNodeStatus = BaseBridgesStatus


@dataclass
class PipeNodeState(BaseBridgesState):
    """
    单次 PipeNode 执行状态追踪对象。

    Attributes:
        status (PipeNodeStatus): 当前执行状态，默认 PENDING
            - PENDING: 待执行
            - RUNNING: 执行中
            - DONE: 执行成功
            - FAILED: 执行失败
            - CANCELED: 已取消

        started_at (datetime | None): 开始执行时间，调用 start() 时设置
        finished_at (datetime | None): 结束执行时间，调用 finish/fail/cancel 时设置
        rows (int): 成功抓取的数据行数，默认 0
        error (str | None): 错误信息，仅在 FAILED 状态时有值
        duration_seconds (float | None): 执行时长（秒），需要 started_at 和 finished_at 都存在
        succeeded (bool): 是否执行成功，等价于 status == DONE
        start_at_repr (str | None): 开始时间的 ISO 格式字符串表示
        finished_at_repr (str | None): 结束时间的 ISO 格式字符串表示

    Methods:
        start(): 标记开始执行，设置状态为 RUNNING，记录开始时间。
        finish(rows: int = 0): 标记执行成功，设置状态为 DONE，记录结束时间和抓取行数。
        fail(error: str): 标记执行失败，设置状态为 FAILED，记录结束时间和错误信息。
        cancel(): 标记执行取消，设置状态为 CANCELED，记录结束时间。
        export(): 导出为字典格式，包含所有状态信息。
        describe(): 返回 JSON 格式的状态信息字符串。

    Example:
        >>> state = PipeNodeState()
        >>> state.status
        ... <PipeNodeStatus.PENDING: 'PENDING'>

        >>> state.start()
        >>> state.status
        ... <PipeNodeStatus.RUNNING: 'RUNNING'>

        >>> state.finish(rows=1000)
        >>> state.succeeded
        ... True
        >>> state.rows
        ... 1000
        >>> state.duration_seconds
        ... 0.123

    """

    status: PipeNodeStatus = PipeNodeStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rows: int = 0
    error: str | None = None

    # ── 状态转换 ──────────────────────────────────────────────
    def start(self) -> None:
        self.status = PipeNodeStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def finish(
        self,
        rows: int = 0,
    ) -> None:
        self.status = PipeNodeStatus.DONE
        self.finished_at = self._get_current_datetime()
        self.rows = rows

    def fail(
        self,
        error: str,
    ) -> None:
        self.status = PipeNodeStatus.FAILED
        self.finished_at = self._get_current_datetime()
        self.error = error

    # ── 只读属性 ──────────────────────────────────────────────

    @property
    def succeeded(self) -> bool:
        return self.status == PipeNodeStatus.DONE

    @property
    def finished(self) -> bool:
        return self.status in {
            PipeNodeStatus.DONE,
            PipeNodeStatus.FAILED,
            PipeNodeStatus.CANCELED,
        }

    def export(self) -> dict:
        result = super().export()
        result["rows"] = self.rows
        result["error"] = self.error
        return result
