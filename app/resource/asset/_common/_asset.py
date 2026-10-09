from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.util.partition import IPartition
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.asset._common._base import GovernedAssetResource


class BaseAsset(
    GovernedAssetResource,
    ABC,
):
    """
    Base class for asset resources

    Attributes:
    ----------
        uri (str):
            Asset URI (e.g., "scheme://bucket/key")
        frn (str):
            Asset FRN (Fortress resource identifier)
        name (str):
            Asset name
        object_pattern (str):
            Pattern for matching asset objects
        partition_pattern (str):
            Pattern for matching asset partitions
        full_pattern (str):
            Full pattern combining object and partition patterns

    Args:
    ----------
        filesystem (AssetFilesystem):
            Asset filesystem type
        platform (Platform):
            Specifies the asset operating platform
        filekind (AssetFileKind):
            Asset file kind, default is AssetFileKind.OBJECT
        partitions (list[str]):
            Partition keys for the asset (e.g., ["year", "month", "day"])
        identity (BaseIdentity | str | None):
            Asset identity
        tags (dict[str, str]):
            Asset tags

    Methods:
    ----------
        assetfile(name: str, partitions: dict[str, str] | None = None) -> BaseAssetfile:
            Construct an assetfile under this asset
        list_assetfiles(since: datetime | float | None = None, until: datetime | float | None = None, recursive: bool = True) -> list[BaseAssetfile]:
            List assetfiles under this asset matching full_pattern, optionally filtered by modified time
        list_objects(pattern: str | None = None, since: datetime | float | None = None, until: datetime | float | None = None, recursive: bool = True) -> list[BaseAssetfile]:
            List assetfiles under this asset matching pattern, optionally filtered by modified time
        export() -> dict[str, Any]:
            Export the asset as a dictionary

    """

    # Enforced public class variables
    # [Inherited] filesystem: ClassVar[AssetFilesystem]
    # [Inherited] platform: ClassVar[Platform]

    # Enforced instance variables
    # [Inherited] identity: BaseIdentity | str | None
    # [Inherited] tags: dict[str, str]
    filekind: AssetFileKind = Field(
        default=AssetFileKind.OBJECT,
        description="[Optional] Asset file kind",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys for the asset",
    )

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

    @abstractmethod
    def assetfile(
        self,
        name: str,
        partitions: dict[str, str] | None = None,
    ) -> BaseAssetfile: ...

    @abstractmethod
    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[BaseAssetfile]: ...

    @abstractmethod
    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
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
