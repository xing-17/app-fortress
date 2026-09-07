from __future__ import annotations

from zoneinfo import ZoneInfo

from app.internal.abstract.utility import IAbstractUtility


class ITimezone(IAbstractUtility):
    """
    Timezone Utility for timezone resolution and management.

    Methods:
        resolve(value: ZoneInfo | str | None = None) -> ZoneInfo:
            Resolve the given value to a ZoneInfo object.

    """

    default: ZoneInfo = ZoneInfo("UTC")

    @staticmethod
    def resolve(value: ZoneInfo | str | None = None) -> ZoneInfo:
        if isinstance(value, ZoneInfo):
            return value
        if isinstance(value, str):
            try:
                return ZoneInfo(value)
            except Exception:
                return ITimezone.default
        if value is None:
            return ITimezone.default
        raise TypeError(f"ITimezone: invalid type to resolve: {type(value)}")
