from __future__ import annotations

import json
import queue
import threading
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.bridges.resources.base.registry import BaseRegistry
from app.bridges.resources._warehouse.warehouse import BridgesWarehouse, ModuleBridgesWarehouse
from app.common.core.setting import GlobalSetting
from app.common.plugin import LogPlugin, StopwatchPlugin, TimePlugin
from app.common.setting.bridges import BridgesSetting
from app.bridges.resources.base.state import BaseBridgesState
from app.common.context.base import BaseContext

TRequest = TypeVar("TRequest", bound=BaseContext)
TState = TypeVar("TState", bound=BaseBridgesState)


class BaseBridgesService(
    Generic[TRequest, TState],
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    """
    Bridges服务基类。

    提供异步队列式任务管理，支持任务提交、状态查询、取消等功能。
    工作线程需通过 start_worker() 显式启动，不在 __init__ 中自动启动。
    
    Worker Loop 行为:
        每次从队列取出一个请求后：
        1. 若请求已取消（CANCELED），清理 _live、持久化 CANCELED 状态后跳过。
        2. 调用 run(request)；若成功，持久化最终状态到 registry。
        3. 若 run() 抛出异常，将状态标记为 FAILED 后持久化，并调用 _on_run_error 钩子。
        4. 无论成败，均调用 _after_run 钩子（error 参数反映是否有异常）。


    Attributes:
        setting (BridgesSetting): 全局 Bridges 配置。
        resources (BridgesWarehouse): 管理所有资源的实例。
        _live (dict[str, TState]): 当前运行中的任务状态字典（request_id -> TState）。
        _live_lock (threading.Lock): 保护 _live 的线程锁。
        _registry (BaseRegistry): 持久化注册表，用于存储历史任务状态。
        _queue (queue.Queue[TRequest]): 任务队列。
        _queue_size_limit (int): 队列最大容量。
        _worker (threading.Thread): 后台工作线程（daemon），串行消费队列。

    Abstract Methods (子类必须实现):
        module_name (property) -> str: 模块名称标识。
        _load_registry() -> BaseRegistry: 创建并返回持久化注册表实例。
        _get_queue_size_limit() -> int: 返回队列最大容量。
        _get_worker_name() -> str: 返回工作线程名称。
        _create_initial_state(request) -> TState: 为请求创建初始状态对象（PENDING）。
        run(request) -> TState: 同步执行单个任务请求，返回最终状态。
        cancel(request_id) -> None: 取消指定请求。

    Hook Methods (子类可选覆盖):
        _before_run(request): 任务执行前调用。
        _on_run_error(request, error): run() 抛出异常时调用。
        _after_run(request, state, error): 任务执行后（无论成败）调用，error 为 None 表示成功。

    Methods:
        start_worker() -> None: 启动后台工作线程（幂等，重复调用安全）。
        submit(request: TRequest) -> str: 异步提交任务请求，返回 request_id。
        lookup(request_id: str) -> dict[str, Any]: 查询任务状态，
            先查 _live（运行中），再查 _registry（历史），均无则抛出 ValueError。
        get_queue_size() -> int: 返回当前队列中等待的任务数。
        shutdown() -> None: 阻塞直至队列全部处理完毕。
        export() -> dict[str, Any]: 导出服务当前状态为字典。
        describe() -> str: 返回服务当前状态的 JSON 字符串。

    Example:
        >>> service = MyBridgesService()
        >>> service.start_worker()
        >>> request = MyBridgesRequest(...)
        >>> request_id = service.submit(request)  # 异步提交
        >>> state = service.lookup(request_id)     # 查询状态
        >>> # 或者同步执行（不经过队列）
        >>> state = service.run(request)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setting: BridgesSetting = GlobalSetting.bridges
        self.resources: BridgesWarehouse = self._load_resources()
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

    def start_worker(self) -> None:
        if not self._worker.is_alive():
            self._worker.start()

    def _load_resources(self) -> BridgesWarehouse:
        return ModuleBridgesWarehouse

    @property
    @abstractmethod
    def module_name(self) -> str: ...

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

    # -- 钩子方法，子类可选择实现 ---------------------

    def _before_run(
        self,
        request: TRequest,
        **kwargs: Any,
    ) -> None:
        pass

    def _on_run_error(
        self,
        request: TRequest,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        pass

    def _after_run(
        self,
        request: TRequest,
        state: TState,
        error: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        if not error:
            self.info(f"_worker_loop: request '{request.id}' OK.")

    # ── 共享实现 ──────────────────────────────────

    def _worker_loop(self) -> None:
        while True:
            request = self._queue.get()
            self._before_run(request=request)  # 可选择实现
            with self._live_lock:
                state = self._live.get(request.id)

            # check if cancelled
            if state and state._is_cancelled():
                with self._live_lock:
                    self._live.pop(request.id, None)
                self._registry.upsert(
                    index=request.id,
                    data=state.export(),
                )
                self._queue.task_done()
                continue

            # setup error variable
            _error: Exception | None = None

            try:
                state = self.run(request)
            except Exception as e:
                _error = e
                self._on_run_error(
                    request=request,
                    error=e,
                )  # 可选择实现

                # mark fail for the state if exists in _live
                with self._live_lock:
                    _state = self._live.get(request.id)
                if _state is not None:
                    _state.fail()
                    state = _state

            finally:
                with self._live_lock:
                    self._live.pop(request.id, None)

                self._after_run(
                    request=request,
                    state=state,
                    error=_error,
                )  # 可选择实现

                if state is not None:
                    self._registry.upsert(
                        index=request.id,
                        data=state.export(),
                    )

                self._queue.task_done()

    def submit(
        self,
        request: TRequest,
    ) -> str:
        with self._live_lock:
            self._live[request.id] = self._create_initial_state(request)
        self._queue.put(request)
        self.debug(f"submit(): queued {request.id} OK.")
        return request.id

    def lookup(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        with self._live_lock:
            if request_id in self._live:
                return self._live[request_id].export()
        result = self._registry.get(request_id)
        if result is None:
            raise ValueError(f"No state found for: {request_id!r}")
        return result

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def shutdown(self) -> None:
        self._queue.join()
        self.info("shutdown: OK.")

    def export(self) -> dict[str, Any]:
        with self._live_lock:
            _live_export = {}
            for rid, s in self._live.items():
                _live_export[rid] = s.export()

        return {
            "module": self.module_name,
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
