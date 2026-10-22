from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass

from app.service.node.dra.errors import DRABusyError

from .session import DRASession


@dataclass
class DRAPoolEntry:
    session: DRASession
    in_use: int = 0
    last_used: float = 0.0
    # Dropped from the pool while busy, the last user closes it
    retired: bool = False


class DRAPool:
    """
    Bounded pool of `DRASession`, one per key

    A new key evicts the least recently used idle session when the pool is full, and idle sessions
    older than `max_idle_seconds` are closed on the next lease. A session that is leased is never
    evicted; when every session is leased a new key gets `DRABusyError`.

    Args:
    ----------
        factory (Callable[[], DRASession]):
            Builds the session of a new key, called under the pool lock
        max_sessions (int):
            Max sessions held at once
        max_idle_seconds (float):
            Idle time before a session is closed, 0 disables
        clock (Callable[[], float]):
            Monotonic seconds, replaceable for tests
        on_close (Callable[[str, str], None] | None):
            Called with (key, reason) after a session is evicted, reason is "lru" or "idle"

    Methods:
    ----------
        lease(key) -> ContextManager[DRASession]:
            Borrow the session of `key`, built on first use
        reset() -> None:
            Close the idle sessions and retire the leased ones
        keys() -> list[str]:
            Keys held, least recently used first
        session(key) -> DRASession | None:
            The session of `key` without leasing it
        stats() -> dict[str, int]:
            "sessions" and "busy_sessions"

    """

    def __init__(
        self,
        factory: Callable[[], DRASession],
        max_sessions: int,
        max_idle_seconds: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        on_close: Callable[[str, str], None] | None = None,
    ) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")

        self._factory = factory
        self._max_sessions = max_sessions
        self._max_idle_seconds = max_idle_seconds
        self._clock = clock
        self._on_close = on_close
        # Least recently used first
        self._entries: OrderedDict[str, DRAPoolEntry] = OrderedDict()
        self._lock = threading.Lock()

    @contextmanager
    def lease(
        self,
        key: str,
    ) -> Generator[DRASession]:
        _entry: DRAPoolEntry = self._acquire(key)
        try:
            yield _entry.session
        finally:
            self._release(_entry)

    def reset(self) -> None:
        _idle: list[DRASession] = []
        with self._lock:
            for _entry in self._entries.values():
                if _entry.in_use:
                    _entry.retired = True
                else:
                    _idle.append(_entry.session)
            self._entries.clear()
        for _session in _idle:
            _session.close()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._entries)

    def session(
        self,
        key: str,
    ) -> DRASession | None:
        with self._lock:
            _entry: DRAPoolEntry | None = self._entries.get(key)
        if _entry is None:
            return None
        return _entry.session

    def stats(self) -> dict[str, int]:
        with self._lock:
            n_busy: int = sum(1 for e in self._entries.values() if e.in_use)
            return {
                "sessions": len(self._entries),
                "busy_sessions": n_busy,
            }

    def _acquire(
        self,
        key: str,
    ) -> DRAPoolEntry:
        _closed: list[tuple[str, str, DRASession]] = []
        try:
            # Built under the lock
            # so one key never ends up with two sessions
            with self._lock:
                _now: float = self._clock()
                _closed.extend(self._pop_expired(_now))
                _entry: DRAPoolEntry | None = self._entries.get(key)
                if _entry is None:
                    _victim: str | None = None
                    if len(self._entries) >= self._max_sessions:
                        _victim = self._lru_idle_key()
                        if _victim is None:
                            raise DRABusyError(f"all {self._max_sessions} sessions are busy")
                    # A failing factory must not cost the pool a healthy session
                    _entry = DRAPoolEntry(session=self._factory())
                    if _victim is not None:
                        _closed.append((_victim, "lru", self._entries.pop(_victim).session))
                    self._entries[key] = _entry
                else:
                    self._entries.move_to_end(key)
                _entry.in_use += 1
                _entry.last_used = _now
                return _entry
        finally:
            # Closing can be slow, keep it out of the lock
            for _key, _reason, _session in _closed:
                _session.close()
                if self._on_close is not None:
                    self._on_close(_key, _reason)

    def _release(
        self,
        entry: DRAPoolEntry,
    ) -> None:
        with self._lock:
            entry.in_use -= 1
            entry.last_used = self._clock()
            _close: bool = entry.retired and entry.in_use == 0
        if _close:
            entry.session.close()

    def _pop_expired(
        self,
        now: float,
    ) -> list[tuple[str, str, DRASession]]:
        if self._max_idle_seconds <= 0:
            return []
        _res: list[tuple[str, str, DRASession]] = []
        for _key, _entry in list(self._entries.items()):
            if _entry.in_use == 0 and now - _entry.last_used > self._max_idle_seconds:
                del self._entries[_key]
                _res.append((_key, "idle", _entry.session))
        return _res

    def _lru_idle_key(self) -> str | None:
        for _key, _entry in self._entries.items():
            if _entry.in_use == 0:
                return _key
        return None
