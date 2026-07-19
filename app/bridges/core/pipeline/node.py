from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.bridges.core.pipeline.context import PipelineContext
from app.bridges.core.pipeline.state import PipelineState
from app.bridges.core.pipenode.context import PipeNodeContext
from app.bridges.core.pipenode.node import PipeNode
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class PipelineNode(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    Pipe 节点。

    负责执行单个 Pipe 任务，通过策略模式将单个数据源派生为多个 PipeNode，
    然后根据 Provider 的并发配置顺序或并发执行这些 PipeNode。

    执行流程：
        1. start() - 标记开始，设置状态为 RUNNING
        2. derive() - 通过策略派生多个 PipeNode
        3. run() - 顺序或并发执行所有 PipeNode
        4. finish() - 收集统计信息，设置最终状态（DONE/PARTIAL/FAILED）

    取消机制：
        - 支持通过 cancel() 方法取消执行
        - 使用 threading.Event 实现取消信号
        - 取消会传播到所有 PipeNode
        - 未开始的节点会被标记为 CANCELED

    Attributes:
        context (PipelineContext): 上下文对象，包含所有配置信息
        request_id (str): 请求 ID
        id (str): 节点 ID（来自 context.id）
        state (PipelineState): 节点状态和统计信息
        pipenodes (list[PipeNode]): 派生的 PipeNode 列表

    Methods:
        derive() -> list[PipeNode]:
            通过策略派生源节点列表。

        cancel() -> None:
            取消当前执行，传播取消信号到所有源节点。

        run() -> PipelineState:
            执行完整的 Pipe 流程，返回执行状态。

        export() -> dict[str, Any]:
            导出节点完整信息为字典。

        describe() -> str:
            导出节点信息为格式化 JSON 字符串。

    Example:
        >>> context = PipelineContext(...)
        >>> pipeline_node = PipelineNode(context)
        >>> state = pipeline_node.run()
        >>> print(state.export())

    """

    def __init__(
        self,
        context: PipelineContext,
    ):
        self.context: PipelineContext = context
        self.request_id: str = context.request_id
        self.id: str = context.id
        self.state: PipelineState = PipelineState()
        self.pipenodes: list[PipeNode] = []
        self._cancel_event = threading.Event()
        self._set_log_prefix(f"PipelineNode({self.id})")

    def derive(self) -> list[PipeNode]:
        self.tick("derive")
        params: dict[str, Any] = self.context.params
        source: BaseSource = self.context.source
        provider: BaseProvider = self.context.provider
        destinations: list[BaseDestination] = self.context.destinations
        provider_type: str = source.setting.provider_type
        strategy_name: str = source.setting.strategy
        strategy_key: tuple[str, str] = (provider_type, strategy_name)
        strategy: BaseStrategy = StrategyFactory.create(strategy_key)
        source_params = strategy.run(
            provider=provider,
            params=params,
        )
        result = []
        for param in source_params:
            source_context = PipeNodeContext(
                request_id=self.request_id,
                pipeline_id=self.id,
                source=source,
                provider=provider,
                destinations=destinations,
                params=param,
            )
            source_node = PipeNode(context=source_context)
            result.append(source_node)

        # Store the derived pipenodes in the instance variable
        self.pipenodes = result
        self.state.total = len(result)

        # Log the derivation result
        duration = self.tock("derive")
        self.info("derive: OK.")
        self.info(f"derive: {len(result)} pipenodes.")
        self.debug(f"derive: duration {duration:.3f}s")
        return result

    def cancel(self) -> None:
        self._cancel_event.set()
        for node in self.pipenodes:
            node.cancel()

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> PipelineState:
        self.tick(f"run({self.id})")
        self.state.start()

        # Derive source nodes if not already derived
        if not self.pipenodes:
            self.pipenodes = self.derive()

        # In case derive failed
        if not self.pipenodes:
            self.warning("run: no pipenodes derived.")
            self.state.finish(self.pipenodes)
            return self.state

        # Update total count for progress tracking
        max_threads: int = self.context.provider.setting.max_threads

        # Run source nodes
        if max_threads > 1:
            self._run_concurrent(max_threads)
        else:
            self._run_sequential()

        # Update state after all source nodes have finished
        self.state.finish(self.pipenodes)

        status = self.state.status.value
        duration = self.tock(f"run({self.id})")
        self.info(f"run: finish with status '{status}'.")
        self.debug(f"run: finish {len(self.pipenodes)} pipenodes.")
        self.debug(f"run: duration {duration:.2f}s.")
        return self.state

    def _run_sequential(self) -> None:
        for node in self.pipenodes:
            if self._is_cancelled():
                node.state.cancel()
                continue
            node.run()
            self.state.update(self.pipenodes)

    def _run_concurrent(
        self,
        max_workers: int,
    ) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for node in self.pipenodes:
                if self._is_cancelled():
                    # PENDING 节点直接标记，不提交
                    node.state.cancel()
                else:
                    # 提交节点执行
                    future = executor.submit(node.run)
                    futures[future] = node

            # 等待所有 future 完成，并处理异常
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.warning(f"source node failed: {e}")

                self.state.update(self.pipenodes)

                # 尝试取消尚未开始执行的排队 future
                if self._is_cancelled():
                    for f, node in futures.items():
                        if f.cancel():
                            node.state.cancel()
                    break

    def export(self) -> dict[str, Any]:
        _export_pipenodes = {}
        for node in self.pipenodes:
            _export_pipenodes[node.id] = node.export()

        return {
            "context": self.context.export(),
            "state": self.state.export(),
            "pipenodes": _export_pipenodes,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
