from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._base import BaseStore
from app.setting._identity import AbstractIdentitySetting
from app.setting._store import FileStoreSetting


class FileStore(BaseStore):
    """
    File store backed by the local filesystem.

    Args:
        name (str): Store name
        path (str | Path | None): File store path, default ./store
        identity (LocalIdentity | AbstractIdentitySetting | str | None): Local identity associated with the file store
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
    identity: LocalIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[NoOps] Local identity associated with the DuckDB store",
    )

    # Class-level attributes
    default_path: ClassVar[str] = "./store/"

    @model_validator(mode="after")
    def _derive_identity(self) -> "FileStore":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_path(self) -> "FileStore":
        _p = IPath.resolve(
            value=self.path,
            default=Path(self.default_path),
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
            identity=setting.identity,
            tags=setting.tags,
        )
