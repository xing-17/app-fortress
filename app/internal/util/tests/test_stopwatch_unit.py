from __future__ import annotations

import asyncio
import threading
import time

import pytest

from app.internal.util.stopwatch import IStopwatch


class TestIStopwatchBasic:
    def test_tock_returns_elapsed_seconds(self) -> None:
        IStopwatch.tick()
        time.sleep(0.05)
        _elapsed = IStopwatch.tock()
        assert 0.05 <= _elapsed < 0.5

    def test_tock_without_tick_raises(self) -> None:
        with pytest.raises(RuntimeError):
            IStopwatch.tock()

    def test_tock_consumes_tick(self) -> None:
        IStopwatch.tick()
        IStopwatch.tock()
        with pytest.raises(RuntimeError):
            IStopwatch.tock()


class TestIStopwatchNesting:
    def test_nested_pairs_in_lifo_order(self) -> None:
        IStopwatch.tick()
        time.sleep(0.1)
        IStopwatch.tick()
        time.sleep(0.02)
        _inner = IStopwatch.tock()
        _outer = IStopwatch.tock()
        assert _inner < _outer
        assert _outer >= 0.12


class TestIStopwatchConcurrency:
    def test_threads_are_isolated(self) -> None:
        _results: dict[str, float] = {}

        def _run(name: str, delay: float) -> None:
            IStopwatch.tick()
            time.sleep(delay)
            _results[name] = IStopwatch.tock()

        _threads = [
            threading.Thread(target=_run, args=("fast", 0.05)),
            threading.Thread(target=_run, args=("slow", 0.2)),
        ]
        for _t in _threads:
            _t.start()
        for _t in _threads:
            _t.join()

        assert 0.05 <= _results["fast"] < 0.2
        assert _results["slow"] >= 0.2

    def test_new_thread_does_not_see_parent_tick(self) -> None:
        IStopwatch.tick()
        _errors: list[Exception] = []

        def _run() -> None:
            try:
                IStopwatch.tock()
            except RuntimeError as e:
                _errors.append(e)

        _t = threading.Thread(target=_run)
        _t.start()
        _t.join()
        IStopwatch.tock()
        assert len(_errors) == 1

    def test_asyncio_tasks_are_isolated(self) -> None:
        async def _work(delay: float) -> float:
            IStopwatch.tick()
            await asyncio.sleep(delay)
            return IStopwatch.tock()

        async def _main() -> list[float]:
            return list(await asyncio.gather(_work(0.05), _work(0.2)))

        _fast, _slow = asyncio.run(_main())
        assert 0.05 <= _fast < 0.2
        assert _slow >= 0.2
