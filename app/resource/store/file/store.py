from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._base import BaseStore
from app.setting._store import FileStoreSetting


class FileStore(BaseStore):
    """
    File store backed by the local filesystem.

    Args:
        name (str): Store name
        path (str | Path | None): File store path, default ./store
        identity (LocalIdentity): Local identity associated with the file store
        storesystem (Literal[StoreSystem.FILE]): Store system type, fixed as FILE
        platform (Literal[Platform.LOCAL]): Store platform type, fixed as LOCAL
        tags (dict[str, str]): Store tags

    Methods:
        from_setting(cls, setting: FileStoreSetting) -> FileStore:
            Create a FileStore instance from a FileStoreSetting object.

    Example:
        >>> from app.resource.store.file.store import FileStore
        >>> store = FileStore(name="my_store", path="/tmp/my_store")
        >>> store.name
        'my_store'

    """

    # Inherited from BaseStore
    # - name: str
    # - tags: dict[str, Any]
    storesystem: Literal[StoreSystem.FILE] = StoreSystem.FILE
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    path: Path | str | None = Field(
        default=None,
        description="[Optional] File store path",
    )
    identity: LocalIdentity = Field(
        default_factory=LocalIdentity.default,
        description="[NoOps] Local identity associated with the DuckDB store",
    )

    @model_validator(mode="after")
    def _derive_path(self) -> "FileStore":
        _p = IPath.resolve(
            self.path,
            default=Path("store"),
            ensure=True,
        )
        if not _p.is_dir():
            raise ValueError(f"Path {self.path} must be a directory")
        object.__setattr__(self, "path", _p)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: FileStoreSetting,
    ) -> FileStore:
        return cls(
            name=setting.name,
            path=setting.path,
            identity=GlobalIdentities.resolve(
                value=getattr(setting, "identity", None),
                platform=Platform.LOCAL,
                default=LocalIdentity.default(),
            ),
            tags=setting.tags,
        )
