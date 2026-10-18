from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.internal.abstract.setting import IAbstractSetting
from app.setting._compute import UnionComputeSetting
from app.setting._identity import UnionIdentitySetting
from app.setting._log import LogSetting
from app.setting._source import UnionSourceSetting
from app.setting._store import UnionStoreSetting
from app.setting._vault import UnionVaultSetting


class SystemLogSetting(LogSetting):
    """
    System-level log setting with a fixed name and file path.

    Attributes:
        name (Literal["system"]): fixed as "system"
        file_path (Literal["./.local/.logs/system"]): fixed as "./.local/.logs/system"

    """

    name: Literal["system"] = "system"
    file_path: Literal["./.local/.logs/system"] = "./.local/.logs/system"


class SystemSetting(IAbstractSetting):
    """
    Fortress system setting.

    Attributes:
        name (str): System name
        alias (str): System alias
        version (str): System version
        timezone (str | None): System timezone
        log (LogSetting): System log configuration, defaults to SystemLogSetting
        identities (list[UnionIdentitySetting]): System identity configurations
        stores (list[UnionStoreSetting]): System metadata store configurations
        vaults (list[UnionVaultSetting]): System asset vault configurations
        sources (list[UnionSourceSetting]): System data source configurations
        computes (list[UnionComputeSetting]): System compute configurations

    """

    # Plain attributes
    name: str = Field(
        default="fortress",
        description="[Optional] System name",
    )
    alias: str = Field(
        default="伽蓝",
        description="[Optional] System alias",
    )

    # System-level configuration attributes
    version: str = Field(
        default="0.0.1",
        description="[Optional] System version",
    )
    timezone: str | None = Field(
        default=None,
        description="[Optional] System timezone",
    )

    # Nested attributes
    log: LogSetting = Field(
        default_factory=SystemLogSetting,
        description="[Optional] System log configuration",
    )
    identities: list[UnionIdentitySetting] = Field(
        default_factory=list,
        description="[Optional] System identity configurations",
    )
    stores: list[UnionStoreSetting] = Field(
        default_factory=list,
        description="[Optional] System metadata store configurations",
    )
    vaults: list[UnionVaultSetting] = Field(
        default_factory=list,
        description="[Optional] System asset vault configurations",
    )
    sources: list[UnionSourceSetting] = Field(
        default_factory=list,
        description="[Optional] System data source configurations",
    )
    computes: list[UnionComputeSetting] = Field(
        default_factory=list,
        description="[Optional] System compute configurations",
    )
