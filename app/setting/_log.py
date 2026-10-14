from __future__ import annotations

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.logformatoption import LogFormatOption
from app.internal.constant.logleveloption import LogLevelOption
from app.internal.util.frn import IFrn


class LogSetting(IAbstractTaggedSetting):
    """
    Log configuration settings.

    Attributes:
    ----------
        name (str): Log name
        level (LogLevelOption | str | None): Log level
        timezone (str | None): Log timezone
        metadata (dict[str, str] | None): Log metadata
        tags (dict[str, str]): Log tags
        console_verbose (bool): Whether the console handler prints
        console_format (LogFormatOption | str | None): Console log format
        file_path (str | None): File log path, eg: ./.log
        file_max_items (int | None): Maximum number of items in the file log

    """

    # Log module attributes
    name: str = Field(
        default="default",
        description="[Optional] Log name",
    )
    level: LogLevelOption | str | None = Field(
        default=LogLevelOption.INFO,
        description="[Optional] Log level",
    )
    timezone: str | None = Field(
        default=None,
        description="[Optional] Log timezone",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="[Optional] Log metadata",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Log tags",
    )

    # Console attributes: used to config console group handler (e.g., stream handler)
    console_verbose: bool = Field(
        default=True,
        description="[Optional] Whether the console handler prints",
    )
    console_format: LogFormatOption | str | None = Field(
        default=LogFormatOption.TEXT,
        description="[Optional] Console log format",
    )

    # File attributes: used to config file group handler (e.g., rotating file handler)

    file_path: str | None = Field(
        default=None,
        description="[Optional] File log path, eg: ./.log",
    )
    file_max_items: int | None = Field(
        default=None,
        description="[Optional] Maximum number of items in the file log",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "setting",
                "log",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        _tags: dict[str, str] = {"name": self.name}
        if self.timezone is not None:
            _tags["timezone"] = self.timezone
        return _tags
