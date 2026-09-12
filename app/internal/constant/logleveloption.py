from __future__ import annotations

from enum import StrEnum


class LogLevelOption(StrEnum):
    """
    Log level Options

    Attributes:
        DEBUG: str = "DEBUG" 调试级别
        INFO: str = "INFO" 信息级别
        WARNING: str = "WARNING" 警告级别
        ERROR: str = "ERROR" 错误级别

    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
