from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.bridges.migrate.request import BridgesMigrateRequest
from app.common.plugin import TimePlugin


class BridgesMigrationStatus(str, Enum):
    """
    BridgesMigrateRequest 的整体状态枚举。

    Attributes:
        PENDING: 请求已创建，尚未开始执行
        RUNNING: 正在执行迁移
        DONE: 迁移成功完成
        FAILED: 迁移失败
        CANCELED: 已在队列中取消（尚未执行）

    Methods:
        value: 返回状态的字符串表示

    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass
class BridgesMigrationState(TimePlugin):
    """
    单次 BridgesMigrateRequest 的执行状态追踪。

    Attributes:
        request: 对应的迁移请求（不可变）
        status: 当前状态（PENDING / RUNNING / DONE / FAILED / CANCELED）
        started_at: 开始时间
        finished_at: 结束时间
        error: 错误信息（FAILED 后填充）
        rows: 写出行数（DONE 后填充）

    Properties:
        duration_seconds: 执行耗时（秒）
        started_at_repr: 开始时间的 ISO 格式字符串
        finished_at_repr: 结束时间的 ISO 格式字符串
        succeeded: 是否执行成功

    Methods:
        start(): 标记迁移开始
        finish(rows): 标记迁移成功完成，记录写出行数
        fail(error): 标记迁移失败，记录错误信息
        cancel(): 标记迁移已取消
        export(): 导出状态为字典
        describe(): 导出状态为 JSON 字符串

    Example:
        >>> state = BridgesMigrationState(request=request)
        >>> state.start()
        >>> state.finish(rows=1000)
        >>> print(state.succeeded)  # True

    """

    request: BridgesMigrateRequest
    status: BridgesMigrationStatus = BridgesMigrationStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    rows: int | None = None

    # ── state transitions ─────────────────────────────────────

    def start(self) -> None:
        self.status = BridgesMigrationStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def finish(
        self,
        rows: int,
    ) -> None:
        self.status = BridgesMigrationStatus.DONE
        self.finished_at = self._get_current_datetime()
        self.rows = rows

    def fail(self, error: str) -> None:
        self.error = error
        self.status = BridgesMigrationStatus.FAILED
        self.finished_at = self._get_current_datetime()

    def cancel(self) -> None:
        self.status = BridgesMigrationStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def _is_cancelled(self) -> bool:
        return self.status == BridgesMigrationStatus.CANCELED

    # ── read-only properties ──────────────────────────────────

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def started_at_repr(self) -> str | None:
        if self.started_at:
            return self.started_at.isoformat()
        return None

    @property
    def finished_at_repr(self) -> str | None:
        if self.finished_at:
            return self.finished_at.isoformat()
        return None

    @property
    def succeeded(self) -> bool:
        return self.status == BridgesMigrationStatus.DONE

    # ── export ─────────────────────────────────────────────────

    def export(self) -> dict[str, Any]:
        return {
            "request_id": self.request.id,
            "status": self.status.value,
            "started_at": self.started_at_repr,
            "finished_at": self.finished_at_repr,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "rows": self.rows,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
