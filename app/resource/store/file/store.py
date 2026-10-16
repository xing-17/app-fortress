from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._store import BaseStore
from app.resource.store.file.database import FileStoreDatabase
from app.resource.store.file.table import FileStoreTable
from app.setting._identity import AbstractIdentitySetting
from app.setting._store import FileStoreSetting


class FileStore(BaseStore):
    """
    File store backed by the local filesystem.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system type, fixed as FILE.
        platform (Platform):
            Store platform type, fixed as LOCAL.

    Args:
    ----------
        name (str):
            Store name
        path (str | Path | None):
            File store path, default ./store
        identity (LocalIdentity | AbstractIdentitySetting | str | None):
            Local identity associated with the file store
        tags (dict[str, str]):
            Store tags

    Methods:
    ----------
        from_setting(cls, setting: FileStoreSetting) -> FileStore:
            Create a FileStore instance from a FileStoreSetting object.
        list_databases() -> list[FileStoreDatabase]:
            Enumerate databases that currently exist under the store path.
        database(name: str) -> FileStoreDatabase:
            Only entry point for building a database under this store.
        table(database: str, name: str, ttl_hours: float | None = None, max_items: int | None = None) -> FileStoreTable:
            Only entry point for building a table under a database of this store.

    Example:
    ----------
        >>> from app.resource.store.file.store import FileStore
        >>> store = FileStore(name="my_store", path="/tmp/my_store")
        >>> store.name
        'my_store'

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    path: Path | str | None = Field(
        default=None,
        description="[Optional] File store path",
    )
    identity: LocalIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[NoOps] Local identity associated with the file store",
    )

    # Class-level attributes
    default_path: ClassVar[str] = "./store/"

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

    @model_validator(mode="after")
    def _derive_identity(self) -> "FileStore":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
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

    def list_databases(self) -> list[FileStoreDatabase]:
        _databases: list[FileStoreDatabase] = []
        _folders = LocalObjectClient.list_folders(
            path=self.path,
            recursive=False,
        )
        for _folder in _folders:
            _database: FileStoreDatabase = FileStoreDatabase(
                name=Path(_folder["path"]).name,
                path=Path(_folder["path"]),
                identity=self.identity,
                _authorized=True,
            )
            _databases.append(_database)
        return _databases

    def database(
        self,
        name: str,
    ) -> FileStoreDatabase:
        _database: FileStoreDatabase = FileStoreDatabase(
            name=name,
            path=self.path / name,
            identity=self.identity,
            _authorized=True,
        )
        return _database

    def table(
        self,
        database: str,
        name: str,
        ttl_hours: float | None = None,
        max_items: int | None = None,
    ) -> FileStoreTable:
        _database: FileStoreDatabase = self.database(database)
        _table: FileStoreTable = _database.table(
            name=name,
            ttl_hours=ttl_hours,
            max_items=max_items,
        )
        return _table
