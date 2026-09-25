from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity


class BaseAssetfile(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for asset file resources

    Args:
        filesystem (AssetFilesystem): Asset filesystem type
        platform (Platform): Asset operating platform
        filekind (AssetFileKind): Asset file kind
        partitions (dict[str, str]): Asset partitions
        size (int | None): Asset size in bytes
        modified_at (float | None): Asset last modified timestamp
        identity (BaseIdentity | str | None): Asset identity
        metadata (dict[str, Any]): Asset metadata
        tags (dict[str, Any]): Asset tags

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
    partitions: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Asset partitions",
    )
    size: int | None = Field(
        default=None,
        description="[Optional] Asset size in bytes",
    )
    modified_at: float | None = Field(
        default=None,
        description="[Optional] Asset last modified timestamp",
    )
    identity: BaseIdentity | str | None = Field(
        default=None,
        description="[Optional] Asset identity",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="[Optional] Asset metadata",
    )
    tags: dict[str, Any] = Field(
        default_factory=dict,
        description="[Optional] Asset tags",
    )

    @property
    @abstractmethod
    def uri(self) -> str: ...

    @property
    @abstractmethod
    def stem(self) -> str: ...

    @property
    @abstractmethod
    def extension(self) -> str: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def read_bytes(self) -> bytes: ...

    @abstractmethod
    def write_bytes(
        self,
        data: bytes,
    ) -> None: ...

    @abstractmethod
    def load(self) -> None: ...

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
