from __future__ import annotations

import json
import queue
import threading
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.bridges.resources.base.registry import BaseRegistry

# from app.bridges.resources._warehouse.warehouse import BridgesWarehouse, ModuleBridgesWarehouse
from app.common.core.setting import GlobalSetting
from app.common.plugin import LogPlugin, StopwatchPlugin, TimePlugin
from app.common.setting.bridges import BridgesSetting

TRequest = TypeVar("TRequest")
TState = TypeVar("TState")


class BaseBridgesService(
    Generic[TRequest, TState],
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    def __init__(self) -> None:
        super().__init__()
        self.setting: BridgesSetting = GlobalSetting.bridges
        # self.resources: BridgesWarehouse = ModuleBridgesWarehouse
        self._live: dict[str, TState] = {}
        self._live_lock = threading.Lock()
        self._registry: BaseRegistry = self._load_registry()
        self._queue_size_limit: int = self._get_queue_size_limit()
        self._queue: queue.Queue[TRequest] = queue.Queue(
            maxsize=self._queue_size_limit,
        )
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=self._get_worker_name(),
        )
        self._worker.start()

    # ── 子类必须实现 ──────────────────────────────

    @abstractmethod
    def _load_registry(self) -> BaseRegistry: ...

    @abstractmethod
    def _get_queue_size_limit(self) -> int: ...

    @abstractmethod
    def _get_worker_name(self) -> str: ...

    @abstractmethod
    def _create_initial_state(
        self,
        request: TRequest,
    ) -> TState: ...

    @abstractmethod
    def run(
        self,
        request: TRequest,
    ) -> TState: ...

    @abstractmethod
    def cancel(
        self,
        request_id: str,
    ) -> None: ...

    # ── 共享实现 ──────────────────────────────────

    def _worker_loop(self) -> None:
        while True:
            request = self._queue.get()
            with self._live_lock:
                state = self._live.get(request.id)
            if state and state._is_cancelled():
                self._queue.task_done()
                continue
            try:
                self.run(request)
            except Exception as e:
                self.error(f"_worker_loop: run() failed for {request.id}: {e}")
            finally:
                self._queue.task_done()
                with self._live_lock:
                    self._live.pop(request.id, None)

    def submit(self, request: TRequest) -> str:
        with self._live_lock:
            self._live[request.id] = self._create_initial_state(request)
        self._queue.put(request)
        self.debug(f"submit(): queued {request.id} OK.")
        return request.id

    def lookup(self, request_id: str) -> dict[str, Any]:
        with self._live_lock:
            if request_id in self._live:
                return self._live[request_id].export()
        result = self._registry.get(request_id)
        if result is None:
            raise ValueError(f"No state found for: {request_id!r}")
        return result

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def export(self) -> dict[str, Any]:
        # 子类可 super().export() 后追加自己的字段
        with self._live_lock:
            _live_export = {}
            for rid, s in self._live.items():
                _live_export[rid] = s.export()

        return {
            "queue": {
                "max_size": self._queue_size_limit,
                "current_size": self.get_queue_size(),
            },
            "live": _live_export,
            "registry": self._registry.export(),
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
