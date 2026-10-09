from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.internal.abstract.utility import IAbstractUtility
from app.internal.util.timezone import ITimezone


class IClock(IAbstractUtility):
    """
    Clock Utility for timezone-aware datetime operations.

    Methods:
        current(timezone: ZoneInfo | str | None = None) -> datetime:
            Return the current time as a timezone-aware datetime object.
        current_iso(timezone: ZoneInfo | str | None = None) -> str:
            Return the current time as an ISO 8601 string.
        current_timestamp(timezone: ZoneInfo | str | None = None) -> float:
            Return the current time as a POSIX timestamp.
        from_datetime(value: datetime, timezone: ZoneInfo | str | None = None) -> datetime:
            Convert a datetime object to a timezone-aware datetime object.
        from_iso(value: str, timezone: ZoneInfo | str | None = None) -> datetime:
            Convert an ISO 8601 string to a timezone-aware datetime object.
        from_timestamp(value: float, timezone: ZoneInfo | str | None = None) -> datetime:
            Convert a POSIX timestamp to a timezone-aware datetime object.

    """

    @staticmethod
    def current(
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        _tz: ZoneInfo = ITimezone.resolve(timezone)
        return datetime.now(tz=_tz)

    @staticmethod
    def current_iso(
        timezone: ZoneInfo | str | None = None,
    ) -> str:
        return IClock.current(timezone).isoformat()

    @staticmethod
    def current_timestamp(
        timezone: ZoneInfo | str | None = None,
    ) -> float:
        return IClock.current(timezone).timestamp()

    @staticmethod
    def current_snapshotdate(
        timezone: ZoneInfo | str | None = None,
    ) -> str:
        return IClock.current(timezone).strftime("%Y-%m-%d")

    @staticmethod
    def from_datetime(
        value: datetime,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        _tz: ZoneInfo = ITimezone.resolve(timezone)
        if value.tzinfo is not None:
            return value.astimezone(tz=_tz)
        else:
            return value.replace(tzinfo=_tz)

    @staticmethod
    def from_iso(
        value: str,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        return IClock.from_datetime(
            datetime.fromisoformat(value),
            timezone=timezone,
        )

    @staticmethod
    def from_timestamp(
        value: float,
        timezone: ZoneInfo | str | None = None,
    ) -> datetime:
        _tz: ZoneInfo = ITimezone.resolve(timezone)
        return datetime.fromtimestamp(value, tz=_tz)
