from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.bridges.base.state import BaseBridgesState, BaseBridgesStatus
from app.bridges.migrate._service.request import MigrateRequest
from app.bridges.migrate.node.node import MigrateNode

MigrateRequestStatus = BaseBridgesStatus


@dataclass(kw_only=True)
class MigrateRequestState(BaseBridgesState):
    """
    单次 MigrateRequest 的执行状态追踪。

    Attributes:
        request: 对应的迁移请求(不可变)
        node: 关联的 MigrateNode 实例(可选)
        status: 当前状态(PENDING / RUNNING / DONE / FAILED / CANCELED)
        started_at: 开始时间(继承自 BaseBridgesState)
        finished_at: 结束时间(继承自 BaseBridgesState)
        error: 错误信息(FAILED 后填充)

    Properties:
        duration_seconds: 执行耗时(秒)(继承)
        started_at_repr: 开始时间 ISO 字符串(继承)
        finished_at_repr: 结束时间 ISO 字符串(继承)
        succeeded: 是否执行成功(status == DONE)
        finished: 是否已结束(DONE / FAILED / CANCELED)

    Methods:
        start(): 标记迁移开始，设置状态为 RUNNING
        finish(): 标记成功完成，设置状态为 DONE
        fail(error): 标记失败，记录错误信息
        cancel(): 标记取消(继承)
        export(): 导出状态为字典
        describe(): 导出为 JSON 字符串(继承)

    Example:
        >>> state = MigrateRequestState(request=request)
        >>> state.start()
        >>> state.finish()
        >>> print(state.succeeded)  # True

    """

    request: MigrateRequest
    node: MigrateNode | None = field(default=None, repr=False)
    error: str | None = None

    # ── 状态转换 ──────────────────────────────────

    def start(self) -> None:
        self.status = MigrateRequestStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def finish(self) -> None:
        self.status = MigrateRequestStatus.DONE
        self.finished_at = self._get_current_datetime()

    def fail(self, error: str) -> None:
        self.error = error
        self.status = MigrateRequestStatus.FAILED
        self.finished_at = self._get_current_datetime()

    # ── 只读属性 ──────────────────────────────────

    @property
    def succeeded(self) -> bool:
        return self.status == MigrateRequestStatus.DONE

    @property
    def finished(self) -> bool:
        return self.status in {
            MigrateRequestStatus.DONE,
            MigrateRequestStatus.FAILED,
            MigrateRequestStatus.CANCELED,
        }

    @property
    def total_rows(self) -> int:
        return self.node.state.rows if self.node else 0

    # ── 导出 ──────────────────────────────────────

    def export(self) -> dict[str, Any]:
        result = super().export()
        if self.node:
            result["node"] = self.node.export()
        else:
            result["node"] = None
        result["request"] = self.request.export()
        result["error"] = self.error
        return result
