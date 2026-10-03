from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, PrivateAttr, model_validator

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

    Args:
        name (str): Store name
        path (str | Path | None): File store path, default ./store
        identity (LocalIdentity | AbstractIdentitySetting | str | None): Local identity associated with the file store
        storesystem (Literal[StoreSystem.FILE]): Store system type, fixed as FILE
        platform (Literal[Platform.LOCAL]): Store platform type, fixed as LOCAL
        tags (dict[str, str]): Store tags

    Attributes:
        databases (list[FileStoreDatabase]): Lazily loaded and cached list of databases under the store.

    Methods:
        from_setting(cls, setting: FileStoreSetting) -> FileStore:
            Create a FileStore instance from a FileStoreSetting object.
        database(name: str) -> FileStoreDatabase:
            Only entry point for building a database under this store.
        list_databases() -> list[FileStoreDatabase]:
            Enumerate databases that currently exist under the store path.
        load_databases(force: bool = False) -> list[FileStoreDatabase]:
            Load (and cache) the databases list, re-scanning when force is True.
        reset_databases() -> None:
            Clear the cached databases list.
        table(database: str, name: str) -> FileStoreTable:
            Retrieve a table under the specified database in this store.

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

    # List of databases under file store
    _databases: list[FileStoreDatabase] | None = PrivateAttr(default=None)

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

    @model_validator(mode="after")
    def _derive_databases(self) -> "FileStore":
        self.load_databases()
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

    @property
    def databases(self) -> list[FileStoreDatabase]:
        self.load_databases()
        return self._databases

    def load_databases(
        self,
        force: bool = False,
    ) -> list[FileStoreDatabase]:
        if force or self._databases is None:
            self._databases = self.list_databases()
        return self._databases

    def reset_databases(self) -> None:
        self._databases = None

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
    ) -> FileStoreTable:
        _database: FileStoreDatabase = self.database(database)
        _table: FileStoreTable = _database.table(name, ttl_hours=ttl_hours)
        return _table
