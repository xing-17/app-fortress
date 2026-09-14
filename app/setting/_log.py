from __future__ import annotations

from app.internal.abstract.setting import IAbstractSetting
from app.internal.constant.logleveloption import LogLevelOption
from app.internal.constant.logformatoption import LogFormatOption
from pydantic import Field


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
        console_format: LogFormatOption | str | None = LogFormatOption.TEXT
            Console日志格式
        file_path: str | None = None
            File日志文件路径, eg: ./log/app.log
        file_max_items: int | None = None
            File日志文件最大条目数

    """

    # Log module attributes
    name: str = Field(
        default="default",
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
    console_verbose: bool = Field(
        default=True,
        description="Console日志是否打印",
    )
    console_format: LogFormatOption | str | None = Field(
        default=LogFormatOption.TEXT,
        description="Console日志格式",
    )

    # File attributes: used to config file group handler (e.g., rotating file handler)

    file_path: str | None = Field(
        default=None,
        description="File日志文件路径, eg: ./log",
    )
    file_max_items: int | None = Field(
        default=None,
        description="File日志文件最大条目数",
    )
