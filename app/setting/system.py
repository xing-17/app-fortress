from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.internal.abstract.setting import IAbstractSetting
from app.setting._identity import UnionIdentitySetting
from app.setting._log import LogSetting
from app.setting._source import UnionSourceSetting
from app.setting._store import UnionStoreSetting


class SystemLogSetting(LogSetting):
    """
    System-level log setting with a fixed name and file path.

    Attributes:
        name (Literal["system"]): 固定为 "system"
        file_path (Literal["./.logs/system"]): 固定为 "./.logs/system"

    """

    name: Literal["system"] = "system"
    file_path: Literal["./.logs/system"] = "./.logs/system"


class SystemSetting(IAbstractSetting):
    """
    Fortress系统设置

    Attributes:
        name (str): 系统名称
        alias (str): 系统别名
        version (str): 系统版本
        timezone (str | None): 系统时区
        log (SystemLogSetting): 系统日志配置
        identities (list[UnionIdentitySetting]): 系统身份配置
        stores (list[UnionStoreSetting]): 系统元数据存储配置
        sources (list[UnionSourceSetting]): 系统数据源配置

    """

    # Plain attributes
    name: str = Field(
        default="fortress",
        description="[Optional] 系统名称",
    )
    alias: str = Field(
        default="伽蓝",
        description="[Optional] 系统别名",
    )
    version: str = Field(
        default="0.0.1",
        description="[Optional] 系统版本",
    )
    timezone: str | None = Field(
        default=None,
        description="[Optional] 系统时区",
    )

    # Nested attributes
    log: SystemLogSetting = Field(
        default_factory=SystemLogSetting,
        description="[Optional] 系统日志配置",
    )
    identities: list[UnionIdentitySetting] = Field(
        default_factory=list,
        description="[Optional] 系统身份配置",
    )
    stores: list[UnionStoreSetting] = Field(
        default_factory=list,
        description="[Optional] 系统元数据存储配置",
    )
    sources: list[UnionSourceSetting] = Field(
        default_factory=list,
        description="[Optional] 系统数据源配置",
    )
