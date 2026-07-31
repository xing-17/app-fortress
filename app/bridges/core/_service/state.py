from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from app.bridges.base.state import BaseBridgesState, BaseBridgesStatus
from app.bridges.core._service.request import CoreRequest
from app.bridges.core.pipeline.state import PipelineStatus
from app.bridges.core.pipenode.state import PipeNodeStatus

if TYPE_CHECKING:
    from app.bridges.core.pipeline.node import PipelineNode

# Re-exported for backward compatibility
__all__ = ["CoreRequestState", "CoreRequestStatus"]


CoreRequestStatus = BaseBridgesStatus


@dataclass(kw_only=True)
class CoreRequestState(BaseBridgesState):
    """
    CoreRequest 的执行状态。

    计数字段（total/done/failed 等）以 PipelineNode 为粒度，反映整体粗粒度状态。
    进度字段（progress/eta 等）以 PipeNode 为粒度，反映更细粒度的实时进度。

    Attributes:
        request:        对应的 CoreRequest（不可变）
        status:         当前状态（PENDING / RUNNING / DONE / PARTIAL / FAILED / CANCELED）
        pipeline_nodes: 该请求派生的所有 PipelineNode
        started_at:     开始时间
        finished_at:    结束时间
        total:          PipelineNode 总数
        done:           状态为 DONE 的 PipelineNode 数（所有 PipeNode 均成功）
        partial:        状态为 PARTIAL 的 PipelineNode 数（部分 PipeNode 成功）
        failed:         状态为 FAILED 的 PipelineNode 数
        running:        状态为 RUNNING 的 PipelineNode 数
        pending:        状态为 PENDING 的 PipelineNode 数
        canceled:       状态为 CANCELED 的 PipelineNode 数

    Properties:
        pipe_nodes:      所有 PipelineNode 下的 PipeNode 展开列表（细粒度）
        total_rows:      所有 PipeNode 成功抓取的总行数
        progress:        基于 PipeNode 维度的完成比例 [0.0, 1.0]
        progress_pct:    progress 的百分比形式（保留一位小数）
        eta_seconds:     基于当前进度估算的剩余时间（秒），未开始时为 None
        elapsed_seconds: 已用时间（秒），运行中时为当前时刻计算值

    """

    type: str = "core_request"
    request: CoreRequest
    pipeline_nodes: list[PipelineNode] = field(default_factory=list)
    total: int = 0
    done: int = 0  # pipes in DONE
    partial: int = 0  # pipes in PARTIAL
    failed: int = 0  # pipes in FAILED
    running: int = 0  # pipes in RUNNING
    pending: int = 0  # pipes in PENDING
    canceled: int = 0  # pipes in CANCELED

    # ── 状态转换 ──────────────────────────────────────────────

    def start(
        self,
        pipeline_nodes: list[PipelineNode],
    ) -> None:
        self.pipeline_nodes = pipeline_nodes
        self.total = len(pipeline_nodes)
        self.pending = self.total
        self.status = CoreRequestStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def update(
        self,
        pipeline_nodes: list[PipelineNode],
    ) -> None:
        states = [n.state for n in pipeline_nodes]
        self.total = len(states)
        self.pending = sum(1 for s in states if s.status == PipelineStatus.PENDING)
        self.running = sum(1 for s in states if s.status == PipelineStatus.RUNNING)
        self.done = sum(1 for s in states if s.status == PipelineStatus.DONE)
        self.partial = sum(1 for s in states if s.status == PipelineStatus.PARTIAL)
        self.failed = sum(1 for s in states if s.status == PipelineStatus.FAILED)
        self.canceled = sum(1 for s in states if s.status == PipelineStatus.CANCELED)

    def finish(
        self,
        pipeline_nodes: list[PipelineNode],
    ) -> None:
        self.pipeline_nodes = pipeline_nodes
        self.update(pipeline_nodes)

        # cancel() 已设置 finished_at 和 status，不再覆盖
        if self._is_cancelled():
            return

        self.finished_at = self._get_current_datetime()
        active = self.done + self.partial
        if active > 0 and self.failed == 0:
            self.status = CoreRequestStatus.DONE
        elif active > 0 and self.failed > 0:
            self.status = CoreRequestStatus.PARTIAL
        elif self.failed > 0:
            self.status = CoreRequestStatus.FAILED
        else:
            self.status = CoreRequestStatus.CANCELED

    # ── 只读属性 ──────────────────────────────────────────────

    @property
    def succeeded(self) -> bool:
        return self.status == CoreRequestStatus.DONE

    @property
    def finished(self) -> bool:
        return self.status in {
            CoreRequestStatus.DONE,
            CoreRequestStatus.PARTIAL,
            CoreRequestStatus.FAILED,
            CoreRequestStatus.CANCELED,
        }

    @property
    def total_rows(self) -> int:
        total = 0
        for pipeline_node in self.pipeline_nodes:
            for pipe_node in pipeline_node.pipenodes:
                total += pipe_node.state.rows
        return total

    @property
    def pipe_nodes(self) -> list:
        result = []
        for pipeline_node in self.pipeline_nodes:
            result.extend(pipeline_node.pipenodes)
        return result

    @property
    def elapsed_seconds(self) -> float | None:
        if not self.started_at:
            return None
        end = self.finished_at or self._get_current_datetime()
        return (end - self.started_at).total_seconds()

    @property
    def progress(self) -> float:
        all_pipe_nodes = self.pipe_nodes
        sn_total = len(all_pipe_nodes)
        if sn_total > 0:
            done = sum(
                1
                for sn in all_pipe_nodes
                if sn.state.status
                not in {
                    PipeNodeStatus.PENDING,
                    PipeNodeStatus.RUNNING,
                }
            )
            return done / sn_total
        else:
            if self.total == 0:
                return 0.0
            completed = sum(
                x
                for x in [
                    self.done,
                    self.partial,
                    self.failed,
                    self.canceled,
                ]
            )
            return completed / self.total

    @property
    def progress_pct(self) -> float:
        return round(self.progress * 100, 1)

    @property
    def eta_seconds(self) -> float | None:
        if self.finished_at:
            return 0.0
        p = self.progress
        if p <= 0:
            return None
        elapsed = self.elapsed_seconds
        if not elapsed:
            return None
        return elapsed / p * (1.0 - p)

    # ── 导出 ──────────────────────────────────────────────────

    def report(self) -> dict[str, Any]:
        result = {}
        result["request"] = self.request.export()
        result["counts"] = {
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "running": self.running,
            "pending": self.pending,
            "partial": self.partial,
            "canceled": self.canceled,
        }
        result["progress"] = {
            "progress": self.progress,
            "progress_pct": self.progress_pct,
            "eta_seconds": self.eta_seconds,
            "elapsed_seconds": self.elapsed_seconds,
        }
        return result

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["request"] = self.request.export()
        result["counts"] = {
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "running": self.running,
            "pending": self.pending,
            "partial": self.partial,
            "canceled": self.canceled,
        }
        result["progress"] = {
            "progress": self.progress,
            "progress_pct": self.progress_pct,
            "eta_seconds": self.eta_seconds,
            "elapsed_seconds": self.elapsed_seconds,
        }
        _pipeline_nodes_export = []
        for pipeline_node in self.pipeline_nodes:
            _pipeline_node_export = pipeline_node.state.export()
            _pipeline_nodes_export.append(_pipeline_node_export)
        result["pipeline_nodes"] = _pipeline_nodes_export
        return result
