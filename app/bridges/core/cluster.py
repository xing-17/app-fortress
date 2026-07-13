from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.bridges.core.registry import BridgesClusterRegistry
from app.bridges.core.request import BridgesRequest
from app.bridges.core.requeststate import BridgesRequestState
from app.bridges.core.resources import BridgesResources, ModuleBridgesResources
from app.bridges.pipelines.context import PipeContext
from app.bridges.pipelines.node import PipeNode
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesSetting


class BridgesCluster(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    Bridges集群。

    负责管理 BridgesResources，并提供统一的资源访问和解析功能。

    Attributes:
        setting (BridgesSetting): 全局 Bridges 配置。
        resources (BridgesResources): 管理所有资源的实例。

    Methods:
        derive(request: BridgesRequest) -> list[PipeContext]: 根据请求解析出 Pipeline 上下文。
        refresh(): 刷新资源。
        export() -> dict[str, str]: 导出资源信息。
        describe() -> str: 返回资源信息的 JSON 字符串。

    """

    def __init__(self):
        self.setting: BridgesSetting = GlobalSetting.bridges
        self.resources: BridgesResources = ModuleBridgesResources
        self._live: dict[str, BridgesRequestState] = {}
        self._registry: BridgesClusterRegistry = self._load_registry()
        self._set_log_prefix("BridgesCluster()")

    def _load_registry(self):
        path = self.setting.bridges.registry_path
        self._registry = BridgesClusterRegistry(path)
        return self._registry

    def derive(
        self,
        request: BridgesRequest,
    ) -> list[PipeNode]:
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
            context = PipeContext(
                request_id=request.id,
                provider=provider,
                source=source,
                destinations=dests,
                params=params,
            )
            node = PipeNode(context)
            nodes.append(node)
        return nodes

    def _derive_destinations(
        self,
        request: BridgesRequest,
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
        request: BridgesRequest,
    ) -> dict[str, Any]:
        return request.params.copy()

    def _derive_sources(
        self,
        request: BridgesRequest,
    ) -> list[BaseSource]:
        sources = self.resources.get_sources_by_tags(
            tags=request.sources_by_tags,
        )
        if not sources:
            raise ValueError("No sources found for the given tags.")
        return sources

    def _derive_providers(
        self,
        request: BridgesRequest,
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
        req_state = self._live.get(request_id)
        if req_state is None:
            return
        for pipe_node in req_state.pipe_nodes:
            pipe_node.cancel()
        req_state.cancel()

    def run(
        self,
        request: BridgesRequest,
    ) -> BridgesRequestState:
        self.tick("run")
        nodes = self.derive(request)
        req_state = BridgesRequestState(request=request)
        self._live[request.id] = req_state

        # Start the request
        req_state.start(nodes)
        self._registry.upsert(
            request_id=request.id,
            data=req_state.export(),
        )

        # Get max_threads from the BridgesSetting
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
                    self._registry.upsert(
                        request_id=request.id,
                        data=req_state.export(),
                    )
                    if req_state._is_cancelled():
                        for f in futures:
                            f.cancel()  # 尝试取消排队中的 future
                        break
        else:
            for node in nodes:
                if req_state._is_cancelled():
                    node.state.cancel()  # 标记未跑的节点为 CANCELED
                    continue
                node.run()
                req_state.update(nodes)
                self._registry.upsert(
                    request_id=request.id,
                    data=req_state.export(),
                )

        # Update final state after all nodes have finished
        req_state.finish(nodes)
        self._registry.upsert(
            request_id=request.id,
            data=req_state.report(),
        )
        self._live.pop(request.id, None)

        # Show duration for the entire run
        duration = self.tock("run")
        self.debug(f"run(): {len(nodes)} pipe nodes finished in {duration:.2f}s")
        return req_state

    def lookup(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        if request_id in self._live:
            return self._live[request_id]

        result: dict[str, Any] | None = self._registry.get(request_id)
        if result is None:
            raise ValueError(f"No request state found for: {request_id}")
        return result

    def refresh(self):
        self.resources.load()

    def export(self) -> dict[str, str]:
        result = {
            "setting": self.setting.export(),
            "resources": self.resources.export(),
            "registry": self._registry.export(),
        }
        return result

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
