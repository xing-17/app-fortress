from __future__ import annotations

from typing import Any

from app.bridges.migrate._service.registry import MigrateRegistry
from app.bridges.migrate._service.request import MigrateRequest
from app.bridges.migrate._service.state import MigrateRequestState
from app.bridges.migrate.node.context import MigrateNodeContext
from app.bridges.migrate.node.node import MigrateNode
from app.bridges.resources.base.service import BaseBridgesService
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.sources.base import BaseSource


class MigrateService(
    BaseBridgesService[MigrateRequest, MigrateRequestState],
):
    """
    数据迁移服务。

    提供异步队列式迁移任务管理，通过 MigrateNode 执行底层迁移。
    执行历史通过 MigrateRegistry 持久化到本地 JSON 文件。

    Attributes:
        setting: BridgesSetting 配置对象
        resources: BridgesWarehouse 资源仓库
        _live: 当前运行中的迁移状态字典（request_id -> MigrateRequestState）
        _registry: MigrateRegistry 持久化注册表
        _queue: 任务队列（Queue[MigrateRequest]）
        _queue_size_limit: 队列最大容量
        _worker: 后台工作线程，串行消费队列

    Methods:
        submit(request): 异步提交迁移请求（入队，立即返回 request_id）
        run(request): 同步执行迁移任务（不经过队列），返回 MigrateRequestState
        lookup(request_id): 查询请求状态（先查 live，再查 registry）
        cancel(request_id): 取消尚在队列中等待的请求
        export(): 导出服务当前状态为字典

    Example:
        >>> service = MigrateService()
        >>> request = MigrateRequest(...)
        >>> request_id = service.submit(request)  # 异步提交
        >>> state = service.lookup(request_id)     # 查询状态
        >>> # 或者同步执行
        >>> state = service.run(request)

    """

    def __init__(self) -> None:
        super().__init__()
        self._set_log_prefix("MigrateService()")

    # ────────────────────INTERNAL─────────────────────────
    @property
    def module_name(self) -> str:
        return "migrate"

    def _load_registry(self) -> MigrateRegistry:
        path: str = self.setting.migrate.registry_path
        max_items: int = self.setting.migrate.max_registry_items
        return MigrateRegistry(
            path=path,
            max_items=max_items,
        )

    def _get_queue_size_limit(self) -> int:
        return self.setting.migrate.max_queue_size

    def _get_worker_name(self) -> str:
        return "migrate-service-worker"

    def _create_initial_state(
        self,
        request: MigrateRequest,
    ) -> MigrateRequestState:
        return MigrateRequestState(request=request)

    # ────────────────────EXTERNAL─────────────────────────

    def derive(
        self,
        request: MigrateRequest,
    ) -> MigrateNode:

        # get source instance from resources
        source_name: str = request.source_name
        source: BaseSource = self.resources.get_source(source_name)

        # Get from destinations
        from_dest_name: str = request.from_destination
        from_dest: BaseDestination = self.resources.get_destination(from_dest_name)
        from_glob: str = request.from_glob

        # Get from destinations
        to_dest_name: str = request.to_destination
        to_dest: BaseDestination = self.resources.get_destination(to_dest_name)
        to_uri_location: str = to_dest.get_duckdb_location()
        to_glob: str = f"{to_uri_location}/source/{source.name}"

        # Get transform_sql, options, extensions
        transform_sql: str | None = request.transform_sql
        req_options: list[str] = request.options
        sys_options: list[str] = self.setting.migrate.options
        options: list[str] = list(set(req_options + sys_options))
        req_extensions: list[str] = request.extensions
        sys_extensions: list[str] = self.setting.migrate.extensions
        extensions: list[str] = list(set(req_extensions + sys_extensions))

        # Create MigrateNodeContext
        context = MigrateNodeContext(
            request_id=request.id,
            source_name=source.name,
            from_destination=from_dest,
            from_glob=from_glob,
            to_destination=to_dest,
            to_glob=to_glob,
            transform_sql=transform_sql,
            options=options,
            extensions=extensions,
        )
        try:
            node = MigrateNode(
                context=context,
            )
            self.debug(f"derive: node '{node.id}' OK.")
            return node
        except Exception as e:
            self.error(f"derive: fail {e}")
            raise

    def plan(
        self,
        request: MigrateRequest,
    ) -> MigrateRequestState:
        node = self.derive(request)
        state = MigrateRequestState(
            request=request,
            node=node,
        )
        state.total = 1
        state.pending = state.total
        return state

    def cancel(
        self,
        request_id: str,
    ) -> None:
        with self._live_lock:
            state: MigrateRequestState | None = self._live.get(request_id)
        if state is None:
            self.warning(f"cancel: request '{request_id}' not found.")
            return
        state.node.cancel()
        state.cancel()

    def run(
        self,
        request: MigrateRequest,
    ) -> MigrateRequestState:
        self.tick(f"run:{request.id}")

        node: MigrateNode = self.derive(request)
        req_state: MigrateRequestState = MigrateRequestState(
            request=request,
            node=node,
        )

        # Register the request state in the live dictionary
        with self._live_lock:
            self._live[request.id] = req_state

        # Start the node
        req_state.start()
        self._registry.upsert(
            request.id,
            req_state.export(),
        )

        node.run()
        if node.state.succeeded:
            req_state.finish()
        elif node.state._is_cancelled():
            if not req_state._is_cancelled():
                req_state.cancel()
        else:
            req_state.fail(node.state.error or "unexpected error")

        self._registry.upsert(
            index=request.id,
            data=req_state.export(),
        )

        # Remove the request state from the live
        with self._live_lock:
            self._live.pop(request.id, None)

        # Show duration for the entire run
        duration = self.tock(f"run:{request.id}")
        _status: str = req_state.status.value
        self.info(f"run: request {request.id} finished with status {_status}")
        self.info(f"run: duration {duration:.2f}s")
        return req_state

    def refresh(
        self,
    ) -> None:
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
