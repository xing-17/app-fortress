from __future__ import annotations

from datetime import UTC, datetime


class IBastionClock:
    """
    Provides UTC clock utilities for timezone-aware datetime operations.

    Methods:
        from_iso(str value): Convert an ISO 8601 string to a timezone-aware UTC datetime.
        from_timestamp(float value): Convert a POSIX timestamp to a timezone-aware UTC datetime.
        current(): Return the current UTC datetime (timezone-aware).
        current_iso(): Return the current UTC time as an ISO 8601 string.
        current_timestamp(): Return the current UTC time as a POSIX timestamp.

    Example:
        ```python
        from bastion._internal.clock import IBastionClock

        # Get current UTC time
        now = IBastionClock.current()

        # Convert from ISO string
        dt = IBastionClock.from_iso("2026-08-14T10:30:00Z")

        # Get timestamp
        timestamp = IBastionClock.current_timestamp()

        # Convert timestamp to datetime
        dt_from_ts = IBastionClock.from_timestamp(1723639800.0)
        ```
    """

    @staticmethod
    def from_iso(value: str) -> datetime | None:
        """Convert an ISO 8601 string to a timezone-aware UTC datetime."""
        if not value:
            return None
        _dt = datetime.fromisoformat(value)
        return _dt if _dt.tzinfo else _dt.replace(tzinfo=UTC)

    @staticmethod
    def from_timestamp(value: float) -> datetime:
        """Convert a POSIX timestamp to a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(value, tz=UTC)

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
