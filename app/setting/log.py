from __future__ import annotations

from app.internal.abstract.setting import IAbstractSetting
from enum import StrEnum

from pydantic import Field


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


class LogFormatOption(StrEnum):
    """
    Log format Options

    Attributes:
        TEXT: str = "TEXT" 纯文本格式
        COLORTEXT: str = "COLORTEXT" 彩色文本格式
        TREE: str = "TREE" 树形结构格式
        COLORTREE: str = "COLORTREE" 彩色树形结构格式

    """

    TEXT = "TEXT"
    COLORTEXT = "COLORTEXT"
    TREE = "TREE"
    COLORTREE = "COLORTREE"


class LogSetting(IAbstractSetting):
    """
    Log configuration settings.

    Attributes:
        name: str
            日志名称
        level: LogLevelOption | str | None = LogLevelOption.INFO
            LOG日志级别
        timezone: str | None = None
            Log日志时区
        metadata: dict[str, str] | None = None
            Log日志元数据
        tags: dict[str, str] | None = None
            Log日志标签
        console_stream: str | None = None
            Console日志输出流, eg: sys.stdout
        console_format: LogFormatOption | str | None = LogFormatOption.TEXT
            Console日志格式
        file_path: str | None = None
            File日志文件路径, eg: ./log/app.log
        file_max_size_mb: int | None = 1
            File日志文件最大大小(MB)

    Examples:
        >>> input = {
        ...     "level": "INFO",
        ...     "format": "COLORTREE",
        ...     "timezone": "Australia/Sydney",
        ...     "path": "./.log/app.log",
        ...     "max_size_mb": 5,
        ... }
        >>> log_setting = LogSetting(**input)
        >>> print(log_setting.describe())

    """

    # Log module attributes
    name: str = Field(
        default=...,
        description="日志名称",
    )
    level: LogLevelOption | str | None = Field(
        default=LogLevelOption.INFO,
        description="LOG日志级别",
    )
    timezone: str | None = Field(
        default=None,
        description="Log日志时区",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Log日志元数据",
    )
    tags: dict[str, str] | None = Field(
        default=None,
        description="Log日志标签",
    )

    # Console attributes: used to config console group handler (e.g., stream handler)

    console_stream: str | None = Field(
        default=None,
        description="Console日志输出流, eg: sys.stdout",
    )
    console_format: LogFormatOption | str | None = Field(
        default=LogFormatOption.TEXT,
        description="Console日志格式",
    )

    # File attributes: used to config file group handler (e.g., rotating file handler)

    file_path: str | None = Field(
        alias="file_path",
        default=None,
        description="File日志文件路径, eg: ./log/app.log",
    )
    file_max_size_mb: int | None = Field(
        default=5,
        description="File日志文件最大大小(MB)",
    )
