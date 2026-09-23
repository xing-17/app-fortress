from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity


class BaseAsset(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for asset resources

    Args:
        filesystem (AssetFilesystem): Asset filesystem type
        platform (Platform): Asset operating platform
        filekind (AssetFileKind): Asset file kind, default is AssetFileKind.OBJECT
        identity (BaseIdentity | str | None): Asset identity
        tags (dict[str, str]): Asset tags

    """

    filesystem: AssetFilesystem = Field(
        ...,
        description="[Required] Asset filesystem type",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Asset operating platform",
    )
    filekind: AssetFileKind = Field(
        default=AssetFileKind.OBJECT,
        description="[Optional] Asset file kind",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys for the asset",
    )
    identity: BaseIdentity | str | None = Field(
        default=None,
        description="[Optional] Asset identity",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Asset tags",
    )

    @property
    @abstractmethod
    def uri(self) -> str: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "filesystem": self.filesystem,
            "filekind": self.filekind,
        }

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res
