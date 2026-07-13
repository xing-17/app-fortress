from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from app.bridges.core.request import BridgesRequest
from app.bridges.pipelines.state import PipeStatus
from app.common.plugin import TimePlugin

if TYPE_CHECKING:
    from app.bridges.pipelines.node import PipeNode


class BridgesRequestStatus(str, Enum):
    """
    BridgesRequest 的状态枚举。

    Attributes:
        PENDING:  请求已创建，但尚未开始执行。
        RUNNING:  请求正在执行中。
        DONE:     请求已成功完成，所有 PipeNode 均为 DONE。
        PARTIAL:  请求部分完成，至少有一个 PipeNode 为 PARTIAL。
        FAILED:   请求失败，所有 PipeNode 均为 FAILED。

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
class BridgesRequestState(TimePlugin):
    """
    单次 BridgesRequest 的执行状态追踪对象。

    Attributes:
        request:     对应的 BridgesRequest（不可变）
        status:      当前状态（PENDING / RUNNING / DONE / PARTIAL / FAILED）
        pipe_nodes:  该请求派生的所有 PipeNode（finish 后填充）
        started_at:  开始时间
        finished_at: 结束时间
        total:       PipeNode 总数
        success:     状态为 DONE 的 PipeNode 数
        partial:     状态为 PARTIAL 的 PipeNode 数
        failed:      状态为 FAILED 的 PipeNode 数
        running:     状态为 RUNNING 的 PipeNode 数
        pending:     状态为 PENDING 的 PipeNode 数

    """

    request: BridgesRequest
    status: BridgesRequestStatus = BridgesRequestStatus.PENDING
    pipe_nodes: list[PipeNode] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total: int = 0
    success: int = 0  # pipes in DONE
    partial: int = 0  # pipes in PARTIAL
    failed: int = 0  # pipes in FAILED
    running: int = 0  # pipes in RUNNING
    pending: int = 0  # pipes in PENDING
    canceled: int = 0  # pipes in CANCELED

    # ── 状态转换 ──────────────────────────────────────────────

    def start(
        self,
        pipe_nodes: list[PipeNode],
    ) -> None:
        self.pipe_nodes = pipe_nodes
        self.total = len(pipe_nodes)
        self.pending = self.total
        self.status = BridgesRequestStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def cancel(self) -> None:
        self.status = BridgesRequestStatus.CANCELED
        self.finished_at = self._get_current_datetime()

    def _is_cancelled(self) -> bool:
        return self.status == BridgesRequestStatus.CANCELED

    def update(
        self,
        pipe_nodes: list[PipeNode],
    ) -> None:
        states = [n.state for n in pipe_nodes]
        self.total = len(states)
        self.pending = sum(1 for s in states if s.status == PipeStatus.PENDING)
        self.running = sum(1 for s in states if s.status == PipeStatus.RUNNING)
        self.success = sum(1 for s in states if s.status == PipeStatus.DONE)
        self.partial = sum(1 for s in states if s.status == PipeStatus.PARTIAL)
        self.failed = sum(1 for s in states if s.status == PipeStatus.FAILED)
        self.canceled = sum(1 for s in states if s.status == PipeStatus.CANCELED)

    def finish(self, pipe_nodes):
        self.pipe_nodes = pipe_nodes
        self.update(pipe_nodes)
        self.finished_at = self._get_current_datetime()
        active = self.success + self.partial
        if active > 0 and self.failed == 0:
            self.status = BridgesRequestStatus.DONE
        elif active > 0 and self.failed > 0:
            self.status = BridgesRequestStatus.PARTIAL
        elif self.failed > 0:
            self.status = BridgesRequestStatus.FAILED
        else:
            self.status = BridgesRequestStatus.CANCELED

    # ── 只读属性 ──────────────────────────────────────────────

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def succeeded(self) -> bool:
        return self.status == BridgesRequestStatus.DONE

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

    @property
    def total_rows(self) -> int:
        total = 0
        for pipe_node in self.pipe_nodes:
            for source_node in pipe_node.source_nodes:
                total += source_node.state.rows
        return total

    @property
    def source_nodes(self) -> list:
        result = []
        for pipe_node in self.pipe_nodes:
            result.extend(pipe_node.source_nodes)
        return result

    # ── 导出 ──────────────────────────────────────────────────

    def export(self) -> dict[str, Any]:
        return {
            "request_id": self.request.id,
            "status": self.status.value,
            "started_at": self.start_at_repr,
            "finished_at": self.finish_at_repr,
            "duration_seconds": self.duration_seconds,
            "total_rows": self.total_rows,
            "pipes": {
                "total": self.total,
                "success": self.success,
                "partial": self.partial,
                "failed": self.failed,
                "running": self.running,
                "pending": self.pending,
                "canceled": self.canceled,
            },
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )

    def report(self) -> dict[str, Any]:
        result = {}
        result.update(self.export())
        result["pipe_nodes"] = []
        for pipe_node in self.pipe_nodes:
            pipe_node_data = {
                "pipe_id": pipe_node.id,
                "status": pipe_node.state.status.value,
                "started_at": pipe_node.state.start_at_repr,
                "finished_at": pipe_node.state.finish_at_repr,
                "duration_seconds": pipe_node.state.duration_seconds,
                "source_nodes": [],
            }

            _source_nodes = []
            for source_node in pipe_node.source_nodes:
                source_node_data = {
                    "source_id": source_node.id,
                    "source_name": source_node.source.name,
                    "params": source_node.params,
                    "status": source_node.state.status.value,
                    "started_at": source_node.state.start_at_repr,
                    "finished_at": source_node.state.finish_at_repr,
                    "duration_seconds": source_node.state.duration_seconds,
                    "rows": source_node.state.rows,
                    "error": source_node.state.error,
                }
                _source_nodes.append(source_node_data)

            pipe_node_data["source_nodes"] = _source_nodes
            result["pipe_nodes"].append(pipe_node_data)
        return result
