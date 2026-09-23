from __future__ import annotations

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.logformatoption import LogFormatOption
from app.internal.constant.logleveloption import LogLevelOption


class LogSetting(IAbstractTaggedSetting):
    """
    Log configuration settings.

    Attributes:
        name (str): 日志名称
        level (LogLevelOption | str | None): LOG日志级别
        timezone (str | None): Log日志时区
        metadata (dict[str, str] | None): Log日志元数据
        tags (dict[str, str]): Log日志标签
        console_verbose (bool): Console日志是否打印
        console_format (LogFormatOption | str | None): Console日志格式
        file_path (str | None): File日志文件路径, eg: ./.log
        file_max_items (int | None): File日志文件最大条目数

    """

    # Log module attributes
    name: str = Field(
        default="default",
        description="[Optional] 日志名称",
    )
    level: LogLevelOption | str | None = Field(
        default=LogLevelOption.INFO,
        description="[Optional] LOG日志级别",
    )
    timezone: str | None = Field(
        default=None,
        description="[Optional] Log日志时区",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="[Optional] Log日志元数据",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Log日志标签",
    )

    # Console attributes: used to config console group handler (e.g., stream handler)
    console_verbose: bool = Field(
        default=True,
        description="[Optional] Console日志是否打印",
    )
    console_format: LogFormatOption | str | None = Field(
        default=LogFormatOption.TEXT,
        description="[Optional] Console日志格式",
    )

    # File attributes: used to config file group handler (e.g., rotating file handler)

    file_path: str | None = Field(
        default=None,
        description="[Optional] File日志文件路径, eg: ./.log",
    )
    file_max_items: int | None = Field(
        default=None,
        description="[Optional] File日志文件最大条目数",
    )

    @property
    def frn(self) -> str:
        return f"setting:log:name={self.name}"

    def _non_override_tags(self) -> dict[str, str]:
        _tags: dict[str, str] = {"name": self.name}
        if self.timezone is not None:
            _tags["timezone"] = self.timezone
        return _tags
