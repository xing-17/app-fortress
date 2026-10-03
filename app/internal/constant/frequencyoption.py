from __future__ import annotations

from enum import StrEnum


class FrequencyOption(StrEnum):
    """
    Frequency Options

    Attributes:
        SECOND: str = "SECOND" per-second frequency
        MINUTE: str = "MINUTE" per-minute frequency
        HOUR: str = "HOUR" per-hour frequency
        DAY: str = "DAY" per-day frequency
        WEEK: str = "WEEK" per-week frequency
        MONTH: str = "MONTH" per-month frequency
        QUARTER: str = "QUARTER" per-quarter frequency
        YEAR: str = "YEAR" per-year frequency

    """

    SECOND = "SECOND"
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"
