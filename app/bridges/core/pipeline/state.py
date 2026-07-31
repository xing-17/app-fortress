from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.bridges.base.state import BaseBridgesState, BaseBridgesStatus

if TYPE_CHECKING:
    from app.bridges.core.pipenode.node import PipeNode as PipeNode

PipelineStatus = BaseBridgesStatus


@dataclass
class PipelineState(BaseBridgesState):
    """
    Pipeline 状态信息

    Attributes:
        status (PipelineStatus): 当前状态
        started_at (datetime | None): 开始时间
        finished_at (datetime | None): 结束时间
        total (int): 总节点数
        done (int): 成功节点数
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
        started_at_repr: 获取开始时间的 ISO 格式字符串
        finished_at_repr: 获取结束时间的 ISO 格式字符串
        export(): 导出状态为字典
        describe(): 导出状态为格式化 JSON 字符串

    Example:
        >>> state = PipelineState()
        >>> state.start()
        >>> state.finish(source_nodes)
        >>> print(state.export())
        >>> print(state.describe())

    """

    type: str = "core_pipeline"
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total: int = 0
    done: int = 0
    failed: int = 0
    running: int = 0
    pending: int = 0
    canceled: int = 0

    def start(self) -> None:
        self.status = PipelineStatus.RUNNING
        self.started_at = self._get_current_datetime()

    def update(
        self,
        pipe_nodes: list[PipeNode],
    ) -> None:
        states = [n.state for n in pipe_nodes]
        self.total = len(states)
        self.pending = sum(1 for s in states if s.status == PipelineStatus.PENDING)
        self.done = sum(1 for s in states if s.status == PipelineStatus.DONE)
        self.failed = sum(1 for s in states if s.status == PipelineStatus.FAILED)
        self.running = sum(1 for s in states if s.status == PipelineStatus.RUNNING)
        self.canceled = sum(1 for s in states if s.status == PipelineStatus.CANCELED)

    def finish(
        self,
        pipe_nodes: list[PipeNode],
    ) -> None:
        self.update(pipe_nodes)
        self.finished_at = self._get_current_datetime()
        if self.done == self.total:
            self.status = PipelineStatus.DONE
        elif self.done > 0:
            self.status = PipelineStatus.PARTIAL
        elif self.failed > 0:
            self.status = PipelineStatus.FAILED
        elif self.total > 0:
            self.status = PipelineStatus.CANCELED  # 有节点但全部被取消
        else:
            self.status = PipelineStatus.DONE  # 无节点，视为成功

    @property
    def succeeded(self) -> bool:
        return self.status == PipelineStatus.DONE

    @property
    def finished(self) -> bool:
        return self.status in {
            PipelineStatus.DONE,
            PipelineStatus.PARTIAL,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELED,
        }

    def export(self) -> dict:
        result = super().export()
        result["counts"] = {
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "running": self.running,
            "pending": self.pending,
            "canceled": self.canceled,
        }
        return result
