from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.identity.local.local import LocalIdentity


class LocalAsset(BaseAsset):
    """
    Local asset contains a collection of local assetfiles.

    Args:
        path (str | Path): Local asset path
        identity (LocalIdentity | str | None): Local asset identity
        filesystem (Literal[AssetFilesystem.LOCAL]): Asset filesystem type, fixed as LOCAL
        platform (Literal[Platform.LOCAL]): Asset platform type, fixed as LOCAL
        tags (dict[str, str]): Local asset tags
    """

    # Inherited from BaseAsset
    # - filekind (AssetFileKind): Asset file kind, default is AssetFileKind.OBJECT
    # - partitions (list[str]): Partition keys for the asset
    # - tags (dict[str, str]): Asset tags
    path: str | Path = Field(
        ...,
        description="[Required] Local asset path",
    )
    identity: LocalIdentity | str | None = Field(
        default_factory=LocalIdentity.default,
        description="[Optional] Local asset identity",
    )
    filesystem: Literal[AssetFilesystem.LOCAL] = AssetFilesystem.LOCAL
    platform: Literal[Platform.LOCAL] = Platform.LOCAL

    @model_validator(mode="after")
    def _derive_path(self) -> "LocalAsset":
        _path: Path = IPath.resolve(self.path, ensure=True)
        if not _path.is_dir():
            raise ValueError(f"Path {self.path} must be a directory")
        object.__setattr__(self, "path", _path)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "LocalAsset":
        _value: LocalIdentity | str | None = self.identity
        _identity: LocalIdentity = GlobalIdentities.resolve(
            value=_value,
            platform=Platform.LOCAL,
            default=LocalIdentity.default(),
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @property
    def uri(self) -> str:
        return f"file://{self.path}"

    @property
    def frn(self) -> str:
        return f"asset:{self.platform}:{self.path}"
