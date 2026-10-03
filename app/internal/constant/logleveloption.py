from __future__ import annotations

from enum import StrEnum


class LogLevelOption(StrEnum):
    """
    Log level Options

    Attributes:
        DEBUG: str = "DEBUG" debug level
        INFO: str = "INFO" info level
        WARNING: str = "WARNING" warning level
        ERROR: str = "ERROR" error level

    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
