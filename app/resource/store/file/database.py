from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._database import BaseDatabase
from app.resource.store.file.table import FileStoreTable
from app.setting._identity import LocalIdentitySetting


class FileStoreDatabase(BaseDatabase):
    """
    File store database backed by a single directory.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system type, fixed as FILE.
        platform (Platform):
            Store platform type, fixed as LOCAL.

    Args:
    ----------
        name (str):
            Database name, single path segment.
        path (Path):
            Database directory path, derived from the parent store path and name.
        identity (LocalIdentity):
            Local identity associated with the database.
        tags (dict[str, str]):
            Database tags

    Methods:
    ----------
        list_tables() -> list[FileStoreTable]:
            Enumerate the *.json tables that currently exist directly under this database.
        table(name: str, ttl_hours: float | None = None) -> FileStoreTable:
            Only entry point for building a table under this database.
        delete(name: str, strict: bool = False) -> None:
            Delete a table's JSON file by name; raises FileNotFoundError if missing and strict is True.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    path: Path = Field(
        ...,
        description="[NoOps] Database directory path, derived from the parent store path and name",
    )
    identity: LocalIdentity | LocalIdentitySetting | str | None = Field(
        ...,
        description="[NoOps] Local identity associated with the database",
    )

    @model_validator(mode="after")
    def _derive_path(self) -> "FileStoreDatabase":
        _p = IPath.resolve(
            value=self.path,
            ensure=True,
        )
        if not _p.is_dir():
            raise ValueError(f"Path {self.path} must be a directory")
        object.__setattr__(self, "path", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "FileStoreDatabase":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "store",
                "database",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"path={self.path}",
            ]
        )

    def list_tables(self) -> list[FileStoreTable]:
        _tables: list[FileStoreTable] = []
        _objects = LocalObjectClient.list_objects(
            path=self.path,
            pattern="*.json",
            recursive=False,
        )
        for _object in _objects:
            _table: FileStoreTable = FileStoreTable(
                name=Path(_object["path"]).stem,
                path=Path(_object["path"]),
                identity=self.identity,
                _authorized=True,
            )
            _tables.append(_table)
        return _tables

    def table(
        self,
        name: str,
        ttl_hours: float | None = None,
    ) -> FileStoreTable:
        return FileStoreTable(
            name=name,
            path=self.path / f"{name}.json",
            identity=self.identity,
            ttl_hours=ttl_hours,
            _authorized=True,
        )

    def delete(
        self,
        name: str,
        strict: bool = False,
    ) -> None:
        _path = self.path / f"{name}.json"
        if _path.exists():
            LocalObjectClient.delete_object(_path)
        elif strict:
            raise FileNotFoundError(f"Table {name} does not exist at path {self.path}")
