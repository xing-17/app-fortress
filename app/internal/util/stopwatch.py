from __future__ import annotations

from contextvars import ContextVar
from time import perf_counter

from app.internal.abstract.utility import IAbstractUtility

# ContextVar is used to store the stack of start times for each thread/asyncio task.
# This ensures that each thread/task has its own independent stopwatch state.
_STARTS: ContextVar[tuple[float, ...]] = ContextVar("stopwatch_starts", default=())


class IStopwatch(IAbstractUtility):
    """
    Stopwatch Utility for measuring elapsed seconds.

    Methods:
    ----------
        tick() -> None:
            Start timing.
        tock() -> float:
            Stop the most recent tick() and return elapsed seconds.
            Raises RuntimeError if there is no matching tick().

    Example:
    ----------
        >>> IStopwatch.tick()
        ... do_work()
        >>> seconds = IStopwatch.tock()
        ... seconds # elapsed time in seconds
    """

    @staticmethod
    def tick() -> None:
        _STARTS.set((*_STARTS.get(), perf_counter()))

    @staticmethod
    def tock() -> float:
        _now: float = perf_counter()
        _starts = _STARTS.get()
        if not _starts:
            raise RuntimeError("tock() called without a matching tick()")
        _STARTS.set(_starts[:-1])
        return _now - _starts[-1]
