from __future__ import annotations

import threading
import time

_INIT_LOCK = threading.Lock()


class StopwatchPlugin:
    """
    计时器混入插件。

    为子类提供线程安全的多键秒表能力，支持同时追踪多个独立命名的计时区间。
    通过混入方式附加到任意类，存储结构在首次访问时按需初始化。

    Attributes:
        _default_key: 未指定名称时使用的默认计时器键名

    Methods:
        tick: 启动一个计时器并返回起始时间戳
        tock: 停止计时器并返回经过的秒数（精确到小数点后4位）

    Example:
        >>> class MyWorker(StopwatchPlugin):
        ...     pass
        >>> worker = MyWorker()
        >>> worker.tick("task")
        >>> elapsed = worker.tock("task")

    """

    _default_key: str = "default"

    @property
    def _stopwatch(self) -> dict[str, float]:
        if not hasattr(self, "_stopwatch_store"):
            with _INIT_LOCK:
                if not hasattr(self, "_stopwatch_store"):
                    self._stopwatch_lock: threading.Lock = threading.Lock()
                    self._stopwatch_store: dict[str, float] = {}
        return self._stopwatch_store

    @staticmethod
    def _resolve_stopwatch_name(name: str | None = None) -> str:
        return name or StopwatchPlugin._default_key

    def tick(
        self,
        name: str | None = None,
    ) -> float:
        name = self._resolve_stopwatch_name(name)
        start = time.perf_counter()
        store = self._stopwatch
        with self._stopwatch_lock:
            store[name] = start

        return start

    def tock(
        self,
        name: str | None = None,
    ) -> float:
        name = self._resolve_stopwatch_name(name)
        store = self._stopwatch
        with self._stopwatch_lock:
            start = store.pop(name, None)

        if start is None:
            return 0.0
        else:
            return round(time.perf_counter() - start, 4)
