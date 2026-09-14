from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.internal.abstract.setting import IAbstractSetting
from app.setting.access import UnionAccessSetting
from app.setting.log import LogSetting


class SystemLogSetting(LogSetting):
    name: Literal["system"] = "system"


class SystemSetting(IAbstractSetting):
    name: str = Field(
        default="fortress",
        description="系统名称",
    )
    alias: str = Field(
        default="伽蓝",
        description="系统别名",
    )
    version: str = Field(
        default="0.0.1",
        description="系统版本",
    )
    timezone: str | None = Field(
        default=None,
        description="系统时区",
    )
    log: SystemLogSetting = Field(
        default_factory=SystemLogSetting,
        description="系统日志配置",
    )
    accesses: list[UnionAccessSetting] = Field(
        default_factory=list,
        description="系统接入配置",
    )
