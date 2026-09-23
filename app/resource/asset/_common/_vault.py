from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._asset import BaseAsset
from app.resource.identity._common._base import BaseIdentity
from app.setting._vault import UnionVaultSetting


class BaseVault(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for asset vault resources

    Args:
        filesystem (AssetFilesystem): Asset vault filesystem type
        platform (Platform): Asset vault operating platform
        name (str | None): Asset vault name
        identity (BaseIdentity | str | None): Asset vault identity
        description (str): Asset vault description information
        tags (dict[str, str]): Asset vault tags

    """

    filesystem: AssetFilesystem = Field(
        ...,
        description="[Required] Asset vault filesystem type",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Asset vault operating platform",
    )
    name: str | None = Field(
        default=None,
        description="[Optional] Asset vault name",
    )
    identity: BaseIdentity | str | None = Field(
        default=None,
        description="[Optional] Asset vault identity",
    )
    description: str = Field(
        default="",
        description="[Optional] Asset vault description information",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Asset vault tags",
    )

    @classmethod
    def from_setting(
        cls,
        setting: UnionVaultSetting,
    ) -> "BaseVault": ...

    @property
    @abstractmethod
    def uri(self) -> str: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    @abstractmethod
    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> "BaseAsset": ...

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "filesystem": self.filesystem,
        }

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res
