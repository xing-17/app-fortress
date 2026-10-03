from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import Field, PrivateAttr

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.partition import IPartition
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity._common._identity import BaseIdentity


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
        partitions (list[str]): Partition keys for the asset
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

    # Cached list of asset files
    _assetfiles: list[BaseAssetfile] | None = PrivateAttr(default=None)

    @property
    def assetfiles(self) -> list[BaseAssetfile]:
        self.load_assetfiles()
        return self._assetfiles

    @property
    @abstractmethod
    def uri(self) -> str: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def object_pattern(self) -> str:
        if self.filekind == AssetFileKind.OBJECT:
            return "*"
        return f"*.{self.filekind.value}"

    @property
    def partition_pattern(self) -> str:
        if not self.partitions:
            return "*"
        return IPartition.to_pattern(self.partitions)

    @property
    @abstractmethod
    def full_pattern(self) -> str: ...

    def load_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        force: bool = False,
    ) -> list[BaseAssetfile]:
        if force or self._assetfiles is None:
            self._assetfiles = self.list_assetfiles(
                since=since,
                until=until,
            )
        return self._assetfiles

    def reset_assetfiles(self) -> None:
        self._assetfiles = None

    @abstractmethod
    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[BaseAssetfile]: ...

    @abstractmethod
    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[BaseAssetfile]: ...

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
