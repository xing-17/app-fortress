from __future__ import annotations

from enum import StrEnum


class FrequencyOption(StrEnum):
    """
    Frequency Options

    Attributes:
        SECOND: str = "SECOND" 每秒频率
        MINUTE: str = "MINUTE" 每分钟频率
        HOUR: str = "HOUR" 每小时频率
        DAY: str = "DAY" 每日频率
        WEEK: str = "WEEK" 每周频率
        MONTH: str = "MONTH" 每月频率
        QUARTER: str = "QUARTER" 每季度频率
        YEAR: str = "YEAR" 每年频率

    """

    SECOND = "SECOND"
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"
