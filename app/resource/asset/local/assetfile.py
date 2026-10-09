from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.local import LocalIdentity


class LocalAssetfile(BaseAssetfile):
    """
    Local assetfile represents a single file on the local filesystem.

    Attributes:
    ----------
        uri (str):
            Local assetfile URI
        frn (str):
            Local assetfile FRN
        stem (str):
            File name without extension
        extension (str):
            File extension
        name (str):
            File name including extension

    Args:
    ----------
        path (str | Path):
            Local assetfile path
        identity (LocalIdentity | str | None):
            Local assetfile identity
        filesystem (Literal[AssetFilesystem.LOCAL]):
            Asset filesystem type, fixed as LOCAL
        platform (Literal[Platform.LOCAL]):
            Asset platform type, fixed as LOCAL
        filekind (AssetFileKind):
            Derived from the path suffix when not explicitly provided
        partitions (dict[str, str]):
            Provided by the owning LocalAsset from its relative "key=value" directories
        size (int | None):
            File size in bytes
        modified_at (float | None):
            File last modified timestamp
        metadata (dict[str, Any]):
            Raw filesystem stat metadata
        tags (dict[str, str]):
            Local assetfile tags

    Methods:
    ----------
        read_bytes() -> bytes:
            Read the file contents as bytes.
        write_bytes(data: bytes) -> None:
            Write bytes to the file, creating parent directories as needed.
        load() -> None:
            Refresh metadata, modified_at and size from the filesystem.

    Example:
    ----------
        >>> assetfile = asset.assetfile("data.csv", partitions={"year": "2026", "month": "01"})
        >>> assetfile.write_bytes(b"col1,col2\\n1,2\\n")
        >>> assetfile.partitions
        {'year': '2026', 'month': '01'}

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] filekind: AssetFileKind
    # [Inherited] partitions: dict[str, str]
    # [Inherited] size: int | None
    # [Inherited] modified_at: float | None
    # [Inherited] metadata: dict[str, Any]
    # [Inherited] tags: dict[str, str]
    path: str | Path = Field(
        ...,
        description="[Required] Local assetfile path",
    )
    identity: LocalIdentity | str | None = Field(
        default_factory=LocalIdentity.default,
        description="[Optional] Local assetfile identity",
    )

    @model_validator(mode="after")
    def _derive_path(self) -> "LocalAssetfile":
        _path: Path = IPath.resolve(self.path)
        object.__setattr__(self, "path", _path)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "LocalAssetfile":
        _identity: LocalIdentity = GlobalIdentities.resolve(
            value=self.identity,
            platform=Platform.LOCAL,
            default=LocalIdentity.default(),
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_filekind(self) -> "LocalAssetfile":
        _val: str = self.path.suffix.lstrip(".").strip().lower()
        for _member in AssetFileKind:
            if _member.value == _val:
                object.__setattr__(self, "filekind", _member)
                break
        else:
            object.__setattr__(self, "filekind", AssetFileKind.OBJECT)
        # tags were snapshotted before filekind was derived; resync now.
        self._update_tags()
        return self

    @property
    def uri(self) -> str:
        return f"file://{self.path}"

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "assetfile",
                f"platform={self.platform}",
                f"path={self.path}",
            ]
        )

    @property
    def name(self) -> str:
        return self.path.name

    def read_bytes(self) -> bytes:
        return LocalObjectClient.read_bytes(self.path)

    def write_bytes(
        self,
        data: bytes,
    ) -> None:
        LocalObjectClient.write_bytes(
            path=self.path,
            data=data,
        )

    def load(self) -> None:
        _meta: dict[str, Any] = LocalObjectClient.get_object(self.path)
        _meta_stat: dict[str, Any] = _meta.get("stat", {})
        if _meta:
            _origin: dict[str, Any] = dict(self.metadata)
            _origin.update(_meta_stat)
            object.__setattr__(self, "metadata", _origin)
        _st_mtime: float | None = _meta_stat.get("st_mtime")
        if _st_mtime is not None:
            object.__setattr__(self, "modified_at", _st_mtime)
        _st_size: int | None = _meta_stat.get("st_size")
        if _st_size is not None:
            object.__setattr__(self, "size", _st_size)
