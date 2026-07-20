from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bridges.migrate._service.request import MigrateRequest

from app.bridges.resources.base.state import BaseBridgesState, BaseBridgesStatus
from app.bridges.migrate.node.node import MigrateNode


MigrationStatus = BaseBridgesStatus


@dataclass(kw_only=True)
class MigrationState(BaseBridgesState):
    """
    单次 MigrateRequest 的执行状态追踪。

    Attributes:
        request: 对应的迁移请求(不可变)
        status: 当前状态(PENDING / RUNNING / DONE / FAILED / CANCELED)
        started_at: 开始时间(继承自 BaseBridgesState)
        finished_at: 结束时间(继承自 BaseBridgesState)
        error: 错误信息(FAILED 后填充)
        rows: 写出行数(DONE 后填充)

    Properties:
        duration_seconds: 执行耗时(秒)(继承)
        started_at_repr: 开始时间 ISO 字符串(继承)
        finished_at_repr: 结束时间 ISO 字符串(继承)
        succeeded: 是否执行成功

    Methods:
        start(): 标记迁移开始
        finish(rows): 标记成功，记录写出行数
        fail(error): 标记失败，记录错误信息
        cancel(): 标记取消(继承)
        export(): 导出状态为字典
        describe(): 导出为 JSON 字符串(继承)

    Example:
        >>> state = MigrationState(request=request)
        >>> state.start()
        >>> state.finish(rows=1000)
        >>> print(state.succeeded)  # True

    """

    request: MigrateRequest
    node: MigrateNode 
    error: str | None = None
    rows: int | None = None

    # ── 状态转换 ──────────────────────────────────

    def start(self) -> None:
        self.status = MigrationStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def finish(self, rows: int) -> None:
        self.status = MigrationStatus.DONE
        self.finished_at = self._get_current_datetime()
        self.rows = rows

    def fail(self, error: str) -> None:
        self.error = error
        self.status = MigrationStatus.FAILED
        self.finished_at = self._get_current_datetime()

    # ── 只读属性 ──────────────────────────────────

    @property
    def succeeded(self) -> bool:
        return self.status == MigrationStatus.DONE

    # ── 导出 ──────────────────────────────────────

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["request"] = self.request.export()
        result["node"] = self.node.export()
        result["error"] = self.error
        result["rows"] = self.rows
        return result
