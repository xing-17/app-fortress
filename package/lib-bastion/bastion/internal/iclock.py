from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_DEFAULT_TZ: ZoneInfo = ZoneInfo("UTC")


class IClock:
    """
    Provides UTC clock utilities for timezone-aware datetime operations.

    Methods:
        from_iso(str value, timezone: str | None = None): Convert an ISO 8601 string to a timezone-aware datetime.
        from_timestamp(float value, timezone: str | None = None): Convert a POSIX timestamp to a timezone-aware datetime.
        current(timezone: ZoneInfo | str | None = None): Return the current datetime (timezone-aware).
        current_iso(timezone: ZoneInfo | str | None = None): Return the current time as an ISO 8601 string.
        current_timestamp(timezone: ZoneInfo | str | None = None): Return the current time as a POSIX timestamp.

    Example:
        ```python
        from bastion._internal.clock import IClock

        # Get current UTC time
        now = IClock.current()

        # Convert from ISO string
        dt = IClock.from_iso("2026-08-14T10:30:00Z")

        # Get timestamp
        timestamp = IClock.current_timestamp()

        # Convert timestamp to datetime
        dt_from_ts = IClock.from_timestamp(1723639800.0)
        ```
    """

    def __init__(self):
        raise TypeError("IClock is not intended to be instantiated")

    @staticmethod
    def _resolve_tz(
        timezone: ZoneInfo | str | None = None,
    ) -> ZoneInfo:
        if isinstance(timezone, ZoneInfo):
            return timezone
        elif isinstance(timezone, str):
            return ZoneInfo(timezone) if timezone else _DEFAULT_TZ
        else:
            return _DEFAULT_TZ
        
    @staticmethod
    def from_datetime(
        value: datetime,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        _tz = IClock._resolve_tz(timezone)
        if value.tzinfo:
            return value.astimezone(_tz)
        else:
            return value.replace(tzinfo=_tz)

    @staticmethod
    def from_iso(
        value: str,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime | None:
        if not value:
            return None
        _tz: ZoneInfo = IClock._resolve_tz(timezone)
        _dt = datetime.fromisoformat(value)
        if _dt.tzinfo:
            return _dt.astimezone(_tz)
        else:
            return _dt.replace(tzinfo=_tz)

    @staticmethod
    def from_timestamp(
        value: float,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        _tz = IClock._resolve_tz(timezone)
        return datetime.fromtimestamp(value, tz=_tz)

    @staticmethod
    def current(timezone: ZoneInfo | str | None = None) -> datetime:
        _tz = IClock._resolve_tz(timezone)
        return datetime.now(_tz)

    @staticmethod
    def current_iso(timezone: ZoneInfo | str | None = None) -> str:
        return IClock.current(timezone).isoformat()

    @staticmethod
    def current_timestamp(timezone: ZoneInfo | str | None = None) -> float:
        return IClock.current(timezone).timestamp()
