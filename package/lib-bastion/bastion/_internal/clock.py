from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class IBastionClock:
    """UTC clock utility for Bastion internals.

    All timestamps produced by this class are timezone-aware UTC.  Consumers
    are responsible for any local-timezone conversion at the presentation layer.

    Example::

        now: datetime = IBastionClock.current()
        ts: float     = IBastionClock.current_timestamp()
    """

    @classmethod
    def current(cls) -> datetime:
        """Return the current UTC datetime (timezone-aware)."""
        return datetime.now(ZoneInfo("UTC"))

    @classmethod
    def current_iso(cls) -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return cls.current().isoformat()

    @classmethod
    def current_timestamp(cls) -> float:
        """Return the current UTC time as a POSIX timestamp."""
        return cls.current().timestamp()
