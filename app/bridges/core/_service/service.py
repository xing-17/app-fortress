from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.bridges.core._service.registry import CoreRegistry
from app.bridges.core._service.request import CoreRequest
from app.bridges.core._service.state import CoreRequestState
from app.bridges.core.pipeline.context import PipelineContext
from app.bridges.core.pipeline.node import PipelineNode
from app.bridges.resources.base.service import BaseBridgesService
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource


class CoreService(
    BaseBridgesService[CoreRequest, CoreRequestState],
):
    """
    Core数据抓取服务类，继承自 BaseBridgesService。

    Attributes:
        _registry (CoreRegistry): Core服务的注册表实例。

    Methods:
        derive(request): 根据请求推导出执行计划的节点列表。
        plan(request): 根据请求生成初始的 CoreRequestState。
        cancel(request_id): 取消指定 request_id 的执行。
        run(request): 执行指定的 CoreRequest，并返回最终的 CoreRequestState。

    """

    def __init__(self):
        super().__init__()
        self._set_log_prefix("CoreService()")

    # ────────────────────INTERNAL─────────────────────────
    @property
    def module_name(self) -> str:
        return "core"

    def _load_registry(self) -> CoreRegistry:
        path: str = self.setting.bridges.registry_path
        max_items: int = self.setting.bridges.max_registry_items
        return CoreRegistry(
            path=path,
            max_items=max_items,
        )

    def _get_queue_size_limit(self) -> int:
        return self.setting.bridges.max_queue_size

    def _get_worker_name(self) -> str:
        return "core-service-worker"

    def _create_initial_state(
        self,
        request: CoreRequest,
    ) -> CoreRequestState:
        return CoreRequestState(request=request)

    # ────────────────────EXTERNAL─────────────────────────

    def derive(
        self,
        request: CoreRequest,
    ) -> list[PipelineNode]:
        # Prepare configs for pipeline
        sources: list[BaseSource] = self._derive_sources(request)
        providers: dict[BaseSource, BaseProvider] = self._derive_providers(
            request=request,
            sources=sources,
        )
        dests: list[BaseDestination] = self._derive_destinations(request)
        params: dict[str, Any] = self._derive_params(request)

        # Prepare pipeline contexts
        nodes = []
        for source, provider in providers.items():
            if not provider:
                raise ValueError(f"No provider found for source: {source.name}")

            # Build context for pipeline
            context = PipelineContext(
                request_id=request.id,
                provider=provider,
                source=source,
                destinations=dests,
                params=params,
            )
            node = PipelineNode(context)
            node.derive()
            nodes.append(node)

        return nodes

    def plan(
        self,
        request: CoreRequest,
    ) -> CoreRequestState:
        nodes: list[PipelineNode] = self.derive(request)
        state = CoreRequestState(
            request=request,
            pipeline_nodes=nodes,
        )
        state.total = len(nodes)
        state.pending = state.total
        return state

    def _derive_destinations(
        self,
        request: CoreRequest,
    ) -> list[BaseDestination]:
        names = request.destinations
        if not names:
            result = self.resources.list_destinations()
        else:
            result = []
            for name in names:
                dest = self.resources.get_destination(name)
                result.append(dest)
        if not result:
            raise ValueError("No destinations found for the given names.")
        return result

    def _derive_params(
        self,
        request: CoreRequest,
    ) -> dict[str, Any]:
        return request.params.copy()

    def _derive_sources(
        self,
        request: CoreRequest,
    ) -> list[BaseSource]:
        sources = self.resources.get_sources_by_tags(
            tags=request.sources_by_tags,
        )
        if not sources:
            raise ValueError("No sources found for the given tags.")
        return sources

    def _derive_providers(
        self,
        request: CoreRequest,
        sources: list[BaseSource],
    ) -> dict[BaseSource, BaseProvider]:
        overrides = request.providers
        result: dict[BaseSource, BaseProvider] = {}
        for source in sources:
            ptype = source.provider_type
            if overrides and ptype in overrides:
                name = overrides[ptype]
                _provider = self.resources.get_provider(name)
                if not _provider:
                    raise ValueError(f"No provider found for source: {source.name}")
                result[source] = _provider
            else:
                _provider = self.resources.get_first_provider_by_type(ptype)
                if not _provider:
                    raise ValueError(f"No provider found for type: {ptype}")
                result[source] = _provider
        return result

    def cancel(
        self,
        request_id: str,
    ) -> None:
        with self._live_lock:
            req_state = self._live.get(request_id)
        if req_state is None:
            self.warning(f"cancel: request '{request_id} not found.")
            return
        for pipeline_node in req_state.pipeline_nodes:
            pipeline_node.cancel()
        req_state.cancel()

    def run(
        self,
        request: CoreRequest,
    ) -> CoreRequestState:
        self.tick(f"run:{request.id}")

        # Init state and pipeline nodes
        nodes: list[PipelineNode] = self.derive(request)
        req_state: CoreRequestState = CoreRequestState(
            request=request,
            pipeline_nodes=nodes,
        )

        # Register the request state in the live dictionary
        with self._live_lock:
            self._live[request.id] = req_state

        # Start the request
        req_state.start(nodes)
        self._registry.upsert(
            index=request.id,
            data=req_state.export(),
        )

        # pipeline 级并发
        max_threads: int = self.setting.bridges.max_threads

        # Run nodes concurrently if max_threads > 1
        if max_threads > 1:
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {}
                for node in nodes:
                    if req_state._is_cancelled():
                        node.state.cancel()  # 提交前检查，直接标记
                    else:
                        future = executor.submit(node.run)
                        futures[future] = node
                for _ in as_completed(futures):
                    req_state.update(nodes)
                    if req_state._is_cancelled():
                        for f, node in futures.items():
                            if f.cancel():
                                node.state.cancel()
                        break
        # Run nodes serially if max_threads <= 1
        else:
            for node in nodes:
                if req_state._is_cancelled():
                    # 标记未跑的节点为 CANCELED
                    node.state.cancel()
                    continue
                node.run()
                req_state.update(nodes)

        # Update final state after all nodes have finished
        req_state.finish(nodes)
        self._registry.upsert(
            index=request.id,
            data=req_state.export(),
        )
        with self._live_lock:
            self._live.pop(request.id, None)

        # Show duration for the entire run
        duration = self.tock(f"run:{request.id}")
        _status: str = req_state.status.value
        _total: int = req_state.total
        _done: int = req_state.done
        _total_rows: int = req_state.total_rows
        self.info(f"run: request {request.id} finished with status {_status}")
        self.info(f"run: total {_total}, done {_done}")
        self.info(f"run: rows {_total_rows}")
        self.info(f"run: duration {duration:.2f}s")
        return req_state

    def refresh(self):
        self.resources.load()

    def is_live(
        self,
        request_id: str,
    ) -> bool:
        with self._live_lock:
            return request_id in self._live

    def history(self) -> list[dict[str, Any]]:
        return self._registry.all()

    def reset(self):
        self.resources.refresh()
        self._registry.reset()

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["setting"] = self.setting.export()
        return result
