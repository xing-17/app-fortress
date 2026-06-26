"""
综合测试：app.common.plugin.stopwatch

覆盖范围
--------
- TestResolve       _resolve_stopwatch_name 默认键名解析
- TestTick          tick() 返回值类型与内部状态
- TestTock          tock() 返回值类型、未 tick 时返回 0、计时合理性
- TestMultipleKeys  多个独立命名计时器互不干扰
- TestThreadSafety  多线程并发 tick/tock 不抛异常
"""

from __future__ import annotations

import threading
import time

from app.common.plugin.stopwatch import StopwatchPlugin

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _Worker(StopwatchPlugin):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# TestResolve
# ──────────────────────────────────────────────────────────────────────────────


class TestResolve:
    def test_none_resolves_to_default_key(self):
        assert StopwatchPlugin._resolve_stopwatch_name(None) == StopwatchPlugin._default_key

    def test_named_key_is_preserved(self):
        assert StopwatchPlugin._resolve_stopwatch_name("job") == "job"

    def test_default_key_is_default(self):
        assert StopwatchPlugin._default_key == "default"


# ──────────────────────────────────────────────────────────────────────────────
# TestTick
# ──────────────────────────────────────────────────────────────────────────────


class TestTick:
    def test_tick_returns_float(self):
        w = _Worker()
        result = w.tick()
        assert isinstance(result, float)

    def test_tick_with_name_returns_float(self):
        w = _Worker()
        result = w.tick("job")
        assert isinstance(result, float)

    def test_tick_stores_entry_in_stopwatch(self):
        w = _Worker()
        w.tick("alpha")
        assert "alpha" in w._stopwatch

    def test_tick_default_key_stored(self):
        w = _Worker()
        w.tick()
        assert StopwatchPlugin._default_key in w._stopwatch

    def test_tick_start_value_is_positive(self):
        w = _Worker()
        start = w.tick("t")
        assert start > 0


# ──────────────────────────────────────────────────────────────────────────────
# TestTock
# ──────────────────────────────────────────────────────────────────────────────


class TestTock:
    def test_tock_without_tick_returns_zero(self):
        w = _Worker()
        assert w.tock("nonexistent") == 0.0

    def test_tock_after_tick_returns_float(self):
        w = _Worker()
        w.tick("task")
        result = w.tock("task")
        assert isinstance(result, float)

    def test_tock_after_tick_returns_non_negative(self):
        w = _Worker()
        w.tick("task")
        assert w.tock("task") >= 0.0

    def test_tock_removes_key_from_store(self):
        w = _Worker()
        w.tick("once")
        w.tock("once")
        assert "once" not in w._stopwatch

    def test_tock_default_key_works(self):
        w = _Worker()
        w.tick()
        elapsed = w.tock()
        assert isinstance(elapsed, float)

    def test_tock_result_rounded_to_4_decimals(self):
        w = _Worker()
        w.tick("r")
        time.sleep(0.01)
        elapsed = w.tock("r")
        assert elapsed == round(elapsed, 4)


# ──────────────────────────────────────────────────────────────────────────────
# TestMultipleKeys
# ──────────────────────────────────────────────────────────────────────────────


class TestMultipleKeys:
    def test_two_named_timers_are_independent(self):
        w = _Worker()
        w.tick("a")
        time.sleep(0.01)
        w.tick("b")
        time.sleep(0.01)
        elapsed_a = w.tock("a")
        elapsed_b = w.tock("b")
        assert elapsed_a > elapsed_b

    def test_tock_one_key_leaves_other_intact(self):
        w = _Worker()
        w.tick("keep")
        w.tick("remove")
        w.tock("remove")
        assert "keep" in w._stopwatch
        assert "remove" not in w._stopwatch


# ──────────────────────────────────────────────────────────────────────────────
# TestThreadSafety
# ──────────────────────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_tick_tock_no_exception(self):
        w = _Worker()
        errors: list[Exception] = []

        def work(key: str) -> None:
            try:
                w.tick(key)
                time.sleep(0.001)
                w.tock(key)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=work, args=(f"thread_{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
