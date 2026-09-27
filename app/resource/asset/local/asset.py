from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset.local._client import LocalObjectClient
from app.resource.asset.local.assetfile import LocalAssetfile
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

    Methods:
        list_assetfiles(since=None, until=None) -> list[LocalAssetfile]:
            List assetfiles under the asset directory matching full_pattern, optionally filtered by modified time.
        list_objects(pattern=None, since=None, until=None) -> list[LocalAssetfile]:
            List assetfiles under the asset directory matching pattern, optionally filtered by modified time.

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
        _identity: LocalIdentity = GlobalIdentities.resolve(
            value=self.identity,
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

    @property
    def name(self) -> str:
        return self.path.name

    # @property: object_pattern from BaseAsset

    # @property: partition_pattern from BaseAsset

    @property
    def full_pattern(self) -> str:
        _obj_expr: str = self.object_pattern
        _base_expr: str = f"{self.path}"
        if not self.partitions:
            # skip the partition segment so files directly under path (no subdirectory) still match
            return f"*{_base_expr}/{_obj_expr}"
        else:
            return f"*{_base_expr}/{self.partition_pattern}/{_obj_expr}"

    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[LocalAssetfile]:
        return self.list_objects(
            pattern=self.full_pattern,
            since=since,
            until=until,
            recursive=recursive,
        )

    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[LocalAssetfile]:
        _files: list[LocalAssetfile] = []
        if not self.path.exists() or not self.path.is_dir():
            return _files

        _targets: list[dict[str, Any]] = LocalObjectClient.list_objects(
            path=self.path,
            pattern=pattern,
            since=since,
            until=until,
            recursive=recursive,
        )
        for _meta in _targets:
            _meta_path: Path = _meta["path"]
            _meta_stat: dict[str, Any] = _meta.get("stat", {})
            _meta_stat = {k: v for k, v in _meta_stat.items() if v is not None}
            _assetfile: LocalAssetfile = LocalAssetfile(
                path=_meta_path,
                identity=self.identity,
                metadata=_meta_stat,
                modified_at=_meta_stat.get("st_mtime"),
                size=_meta_stat.get("st_size"),
                tags=self.tags,
            )
            _files.append(_assetfile)
        return _files
