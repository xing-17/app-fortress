from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.partition import IPartition
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._mount import DRAMount
from app.resource.asset.local.assetfile import LocalAssetfile
from app.resource.identity.local import LocalIdentity


class LocalAsset(BaseAsset):
    """
    Local asset represents a directory of local files, optionally partitioned into subdirectories.

    Attributes:
    ----------
        uri (str):
            Local asset URI
        frn (str):
            Local asset FRN
        name (str):
            Local asset name (directory name)
        object_pattern (str):
            Glob pattern matching files by filekind
        partition_pattern (str):
            Glob pattern matching partition subdirectories
        full_pattern (str):
            Combined glob pattern matching assetfiles under this asset

    Args:
    ----------
        path (str | Path):
            Local asset path, must be an existing directory
        identity (LocalIdentity | str | None):
            Local asset identity
        filesystem (Literal[AssetFilesystem.LOCAL]):
            Asset filesystem type, fixed as LOCAL
        platform (Literal[Platform.LOCAL]):
            Asset platform type, fixed as LOCAL
        filekind (AssetFileKind):
            Asset file kind, default is AssetFileKind.OBJECT
        partitions (list[str]):
            Declared partition keys for the asset (e.g., ["year", "month"])
        tags (dict[str, str]):
            Local asset tags

    Methods:
    ----------
        get_dra_mount() -> DRAMount:
            Get the DRA mount settings for this asset
        list_assetfiles(since=None, until=None, recursive=True) -> list[LocalAssetfile]:
            List assetfiles under this asset matching full_pattern, optionally filtered by modified time.
        list_objects(pattern=None, since=None, until=None, recursive=True) -> list[LocalAssetfile]:
            List assetfiles under this asset matching an arbitrary pattern.
        assetfile(name, partitions=None) -> LocalAssetfile:
            Construct a LocalAssetfile under this asset, rejecting partitions that don't match
            the declared keys or paths that escape the asset.

    Example:
    ----------
        >>> vault = LocalVault.from_setting(LocalVaultSetting(name="my_vault", path="/tmp/my_vault"))
        >>> asset = vault.asset("prices", partitions=["year", "month"])
        >>> assetfile = asset.assetfile("data.csv", partitions={"year": "2026", "month": "01"})

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] filekind: AssetFileKind
    # [Inherited] partitions: list[str]
    # [Inherited] tags: dict[str, str]
    path: str | Path = Field(
        ...,
        description="[Required] Local asset path",
    )
    identity: LocalIdentity | str | None = Field(
        default_factory=LocalIdentity.default,
        description="[Optional] Local asset identity",
    )

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
        return IFrn.resolve(
            [
                "asset",
                f"platform={self.platform}",
                f"path={self.path}",
            ]
        )

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

    def get_dra_mount(self) -> DRAMount:
        _root: str = self.path.as_posix()
        _mount_glob: str = self._mount_glob(_root)
        return DRAMount(
            scheme="file",
            pattern=_mount_glob,
            scope=f"{_root}/",
            partitions=self.partitions,
        )

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
            # only extract partitions from the relative path
            try:
                _parts = _meta_path.relative_to(self.path).parent.parts
                _rel_segments: list[str] = list(_parts)
            except ValueError:
                _rel_segments = []
            _assetfile: LocalAssetfile = LocalAssetfile(
                path=_meta_path,
                identity=self.identity,
                partitions=IPartition.resolve(_rel_segments),
                metadata=_meta_stat,
                modified_at=_meta_stat.get("st_mtime"),
                size=_meta_stat.get("st_size"),
                tags=self.tags,
                _authorized=True,
            )
            _files.append(_assetfile)
        return _files

    def assetfile(
        self,
        name: str,
        partitions: dict[str, str] | None = None,
    ) -> LocalAssetfile:
        _partitions: dict[str, str] = partitions or {}

        # Ensure partitions are consistent
        _ptn_keys: set[str] = set(_partitions.keys())
        if _ptn_keys != set(self.partitions):
            raise ValueError(f"Partitions must be {self.partitions}, got {list(_ptn_keys)}")

        # Construct the full path for the assetfile
        _ordered: dict[str, str] = {k: _partitions[k] for k in self.partitions}
        _rel: Path = IPartition.to_string(_ordered)

        # resolve before escape check unresolved ".." segments
        _full_path: Path = (self.path / _rel / name).expanduser().resolve()
        if not _full_path.is_relative_to(self.path):
            raise ValueError(f"Assetfile path can not escape {self.path}")

        # create instance
        _assetfile: LocalAssetfile = LocalAssetfile(
            path=_full_path,
            identity=self.identity,
            partitions=_ordered,
            tags=self.tags,
            _authorized=True,
        )
        if _assetfile.filekind != self.filekind:
            raise ValueError(f"Filekind must be {self.filekind}, got {_assetfile.filekind}")
        return _assetfile
