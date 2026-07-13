from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.bridges.pipelines.context import PipeContext
from app.bridges.pipelines.state import PipeState
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy
from app.bridges.sources.context import SourceContext
from app.bridges.sources.node import SourceNode
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class PipeNode(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    Pipe 节点。

    负责执行单个 Pipe 任务，通过策略模式将单个数据源派生为多个 SourceNode，
    然后根据 Provider 的并发配置顺序或并发执行这些 SourceNode。

    执行流程：
        1. start() - 标记开始，设置状态为 RUNNING
        2. derive() - 通过策略派生多个 SourceNode
        3. run() - 顺序或并发执行所有 SourceNode
        4. finish() - 收集统计信息，设置最终状态（DONE/PARTIAL/FAILED）

    取消机制：
        - 支持通过 cancel() 方法取消执行
        - 使用 threading.Event 实现取消信号
        - 取消会传播到所有 SourceNode
        - 未开始的节点会被标记为 CANCELED

    Attributes:
        context (PipeContext): 上下文对象，包含所有配置信息
        request_id (str): 请求 ID
        id (str): 节点 ID（来自 context.id）
        state (PipeState): 节点状态和统计信息
        source_nodes (list[SourceNode]): 派生的源节点列表

    Methods:
        derive() -> list[SourceNode]:
            通过策略派生源节点列表。

        cancel() -> None:
            取消当前执行，传播取消信号到所有源节点。

        run() -> PipeState:
            执行完整的 Pipe 流程，返回执行状态。

        export() -> dict[str, Any]:
            导出节点完整信息为字典。

        describe() -> str:
            导出节点信息为格式化 JSON 字符串。

    Example:
        >>> context = PipeContext(...)
        >>> pipe_node = PipeNode(context)
        >>> state = pipe_node.run()
        >>> print(state.export())

    """

    def __init__(
        self,
        context: PipeContext,
    ):
        self.context: PipeContext = context
        self.request_id: str = context.request_id
        self.id: str = context.id
        self.state: PipeState = PipeState()
        self.source_nodes: list[SourceNode] = []
        self._cancel_event = threading.Event()
        self._set_log_prefix(f"PipeNode({self.id})")

    def derive(self) -> list[SourceNode]:
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
            source_context = SourceContext(
                request_id=self.request_id,
                pipeline_id=self.id,
                source=source,
                provider=provider,
                destinations=destinations,
                params=param,
            )
            source_node = SourceNode(context=source_context)
            result.append(source_node)

        duration = self.tock("derive")
        self.debug(f"derive(): {len(result)} source nodes derived in {duration:.2f}s")
        return result

    def cancel(self) -> None:
        self._cancel_event.set()
        for node in self.source_nodes:
            node.cancel()

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> PipeState:
        self.tick("run")
        self.state.start()
        self.source_nodes = self.derive()  # Strategy 展开
        if not self.source_nodes:
            self.warning("run(): no source nodes derived.")
            self.state.finish(self.source_nodes)
            return self.state

        self.state.total = len(self.source_nodes)  # Run 每个 SourceNode
        # ← 读当前 provider 的并发配置
        max_threads: int = self.context.provider.setting.max_threads

        # Run source nodes
        if max_threads > 1:
            self._run_concurrent(max_threads)
        else:
            self._run_sequential()

        # Update state after all source nodes have finished
        self.state.finish(self.source_nodes)
        duration = self.tock("run")
        self.debug(f"run(): {len(self.source_nodes)} source nodes finished in {duration:.2f}s")
        return self.state

    def _run_sequential(self) -> None:
        for node in self.source_nodes:
            if self._is_cancelled():
                node.state.cancel()  # 标记未跑的节点为 CANCELED
                continue
            node.run()
            self.state.update(self.source_nodes)

    def _run_concurrent(
        self,
        max_workers: int,
    ) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for node in self.source_nodes:
                if self._is_cancelled():
                    node.state.cancel()  # PENDING 节点直接标记，不提交
                else:
                    future = executor.submit(node.run)
                    futures[future] = node

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.warning(f"source node failed: {e}")

                self.state.update(self.source_nodes)

                if self._is_cancelled():
                    for f in futures:
                        f.cancel()  # 尝试取消尚未开始执行的排队 future
                    break

    def export(self) -> dict[str, Any]:
        return {
            "context": self.context.export(),
            "state": self.state.export(),
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
