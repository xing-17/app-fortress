from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.resource.asset._common._base import GovernedAssetResource


class BaseAssetfile(
    GovernedAssetResource,
    ABC,
):
    """
    Base class for assetfile resources

    Attributes:
    ----------
        uri (str):
            Asset URI (e.g., "scheme://bucket/key")
        frn (str):
            Asset FRN (Fortress resource identifier)
        stem (str):
            Asset file stem (name without extension)
        extension (str):
            Asset file extension
        name (str):
            Asset file name

    Args:
    ----------
        filesystem (AssetFilesystem):
            Asset filesystem type
        platform (Platform):
            Asset operating platform
        filekind (AssetFileKind):
            Asset file kind
        partitions (dict[str, str]):
            Asset partitions
        size (int | None):
            Asset size in bytes
        modified_at (float | None):
            Asset last modified timestamp
        identity (BaseIdentity | str | None):
            Asset identity
        metadata (dict[str, Any]):
            Asset metadata
        tags (dict[str, str]):
            Asset tags

    Methods:
    ----------
        read_bytes() -> bytes:
            Read the asset file as bytes
        write_bytes(data: bytes) -> None:
            Write bytes to the asset file
        load() -> None:
            Load the asset file metadata from storage

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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="[Optional] Asset metadata",
    )

    @property
    @abstractmethod
    def stem(self) -> str: ...

    @property
    @abstractmethod
    def extension(self) -> str: ...

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
        _res: dict[str, str] = super()._non_override_tags()
        _res["filekind"] = self.filekind
        return _res
