from __future__ import annotations

from datetime import UTC, datetime


class IBastionClock:
    """
    UTC clock utility.

    All timestamps are timezone-aware UTC.
    """

    @staticmethod
    def current() -> datetime:
        """Return the current UTC datetime (timezone-aware)."""
        return datetime.now(UTC)

    @staticmethod
    def current_iso() -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return IBastionClock.current().isoformat()

    @staticmethod
    def current_timestamp() -> float:
        """Return the current UTC time as a POSIX timestamp."""
        return IBastionClock.current().timestamp()
