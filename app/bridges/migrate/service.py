from __future__ import annotations

import json
import queue
import threading
from typing import Any

from app.bridges.migrate.node import BridgesMigrationNode
from app.bridges.migrate.registry import BridgesMigrateRegistry
from app.bridges.migrate.request import BridgesMigrateRequest
from app.bridges.migrate.state import BridgesMigrationState, BridgesMigrationStatus
from app.bridges.resources._warehouse.warehouse import BridgesWarehouse, ModuleBridgesWarehouse
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesSetting


class BridgesMigrationService(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    数据迁移服务，对标 BridgesCoreCluster。

    提供异步队列式迁移任务管理，通过 BridgesMigrationNode 执行底层迁移。
    执行历史通过 BridgesMigrateRegistry 持久化到本地 JSON 文件。

    Attributes:
        setting: BridgesSetting 配置对象
        resources: BridgesWarehouse 资源仓库
        _live: 当前运行中的迁移状态字典（request_id -> BridgesMigrationState）
        _registry: BridgesMigrateRegistry 持久化注册表
        _queue: 任务队列（Queue[BridgesMigrateRequest]）
        _queue_size_limit: 队列最大容量
        _worker: 后台工作线程，串行消费队列

    Methods:
        submit(request): 异步提交迁移请求（入队，立即返回 request_id）
        run(request): 同步执行迁移任务（不经过队列），返回 BridgesMigrationState
        lookup(request_id): 查询请求状态（先查 live，再查 registry）
        cancel(request_id): 取消尚在队列中等待的请求
        export(): 导出服务当前状态为字典

    Example:
        >>> service = BridgesMigrationService()
        >>> request = BridgesMigrateRequest(...)
        >>> request_id = service.submit(request)  # 异步提交
        >>> state = service.lookup(request_id)     # 查询状态
        >>> # 或者同步执行
        >>> state = service.run(request)

    """

    def __init__(self) -> None:
        super().__init__()
        self.setting: BridgesSetting = GlobalSetting.bridges
        self.resources: BridgesWarehouse = ModuleBridgesWarehouse
        self._live: dict[str, BridgesMigrationState] = {}
        self._registry: BridgesMigrateRegistry = self._load_registry()
        # 串行队列
        self._queue_size_limit: int = self.setting.migrate.max_queue_size
        self._queue: queue.Queue[BridgesMigrateRequest] = queue.Queue(
            maxsize=self._queue_size_limit,
        )
        # 串行消费队列
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="BridgesMigration",
        )
        self._worker.start()
        self._set_log_prefix("BridgesMigration()")

    # ────────────────────INTERNAL─────────────────────────

    def _load_registry(self) -> BridgesMigrateRegistry:
        path: str = self.setting.migrate.registry_path
        self._registry = BridgesMigrateRegistry(path)
        return self._registry

    def _worker_loop(self) -> None:
        while True:
            request = self._queue.get()
            state = self._live.get(request.id)

            # Skip requests cancelled while waiting in the queue
            if state and state._is_cancelled():
                self._queue.task_done()
                continue
            try:
                self.run(request)
            except Exception as e:
                self.error(f"_worker_loop: run() failed for {request.id}: {e}")
            finally:
                self._queue.task_done()

    # ────────────────────EXTERNAL─────────────────────────

    def submit(
        self,
        request: BridgesMigrateRequest,
    ) -> str:
        self._live[request.id] = BridgesMigrationState(
            request=request,
        )
        self._queue.put(request)
        self.debug(f"submit(): queued {request.id} OK.")
        return request.id

    def run(
        self,
        request: BridgesMigrateRequest,
    ) -> BridgesMigrationState:
        self.tick(f"run:{request.id}")

        # Check for pre-run cancel (request was cancelled while waiting in queue)
        queued_state = self._live.get(request.id)
        if queued_state and queued_state._is_cancelled():
            self._live.pop(request.id, None)
            duration = self.tock(f"run:{request.id}")
            self.debug(f"run(): {request.id} skipped (CANCELED) in {duration:.2f}s")
            return queued_state

        # Create node — node owns its DuckDB client and state transitions
        try:
            node = BridgesMigrationNode(
                setting=self.setting.migrate,
                request=request,
            )
        except Exception as e:
            state = self._live.pop(request.id, BridgesMigrationState(request=request))
            state.fail(str(e))
            self._registry.upsert(request.id, state.export())
            self.tock(f"run:{request.id}")
            self.error(f"run(): node setup failed for {request.id}: {e}")
            return state

        # Expose node's live state in _live so lookup() reflects real-time progress
        self._live[request.id] = node.state
        self._registry.upsert(request.id, node.state.export())

        node.run()  # state.start() → execute → state.finish() / state.fail()

        self._registry.upsert(request.id, node.state.export())
        self._live.pop(request.id, None)

        duration = self.tock(f"run:{request.id}")
        self.info(f"run(): {request.id} → {node.state.status.value} OK")
        self.info(f"run(): ({node.state.rows} rows, {duration:.2f}s)")
        return node.state

    def lookup(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        if request_id in self._live:
            return self._live[request_id].export()
        result = self._registry.get(request_id)
        if result is None:
            raise ValueError(f"No migration state found for: {request_id!r}")
        return result

    def cancel(
        self,
        request_id: str,
    ) -> None:
        state: BridgesMigrationState = self._live.get(request_id)
        if state and state.status == BridgesMigrationStatus.PENDING:
            state.cancel()
            self._registry.upsert(request_id, state.export())
            self.debug(f"cancel(): {request_id} marked CANCELED")

    def export(self) -> dict[str, Any]:
        _export_live = {}
        for k, v in self._live.items():
            _export_live[k] = v.export()

        return {
            "queue": {
                "max_size": self._queue_size_limit,
                "current_size": self._queue.qsize(),
            },
            "registry": self._registry.export(),
            "live": _export_live,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
