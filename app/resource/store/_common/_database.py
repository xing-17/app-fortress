from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import Field, PrivateAttr

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.resource.identity._common._base import BaseIdentity
from app.resource.store._common._base import GovernedStoreResource
from app.resource.store._common._table import BaseTable
from app.setting._identity import AbstractIdentitySetting


class BaseDatabase(
    GovernedStoreResource,
    ABC,
):
    """
    Base class for store database resources, governed and derived from a parent store.

    A database can only be constructed via its parent store's `database()` method, which
    guarantees the database occupies exactly one path segment directly under the store
    (no nested names). Databases have no write capability of their own; write capability
    only exists on `BaseTable`, which in turn can only be derived from a database.

    Args:
        name (str): Database name, must be a single path segment (no nested separators)
        storesystem (StoreSystem): Store system
        platform (Platform): Store platform
        identity (BaseIdentity | AbstractIdentitySetting | str | None): Database identity
        tags (dict[str, str]): Database tags

    Attributes:
        tables (list[BaseTable]): Lazily loaded and cached list of tables under the database.

    Methods:
        table(name: str) -> BaseTable:
            Only entry point for building a table under this database.
        list_tables() -> list[BaseTable]:
            Enumerate tables that currently exist under this database.
        load_tables(force: bool = False) -> list[BaseTable]:
            Load (and cache) the tables list, re-scanning when force is True.
        reset_tables() -> None:
            Clear the cached tables list.
        delete(name: str, strict: bool = False) -> None:
            Delete a table by name; raises if missing and strict is True.

    """

    name: str = Field(
        ...,
        description="[Required] Database name, single path segment governed by the parent store",
    )
    storesystem: StoreSystem = Field(
        ...,
        description="[Required] Store system",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Store platform",
    )
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Database identity",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Database tags",
    )

    # List of tables under database
    _tables: list[BaseTable] | None = PrivateAttr(default=None)

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "store",
                "database",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"name={self.name}",
            ]
        )

    @property
    def tables(self) -> list[BaseTable]:
        self.load_tables()
        return self._tables

    def load_tables(
        self,
        force: bool = False,
    ) -> list[BaseTable]:
        if force or self._tables is None:
            self._tables = self.list_tables()
        return self._tables

    def reset_tables(self) -> None:
        self._tables = None

    @abstractmethod
    def list_tables(self) -> list[BaseTable]: ...

    @abstractmethod
    def table(
        self,
        name: str,
    ) -> BaseTable: ...

    @abstractmethod
    def delete(
        self,
        name: str,
        strict: bool = False,
    ) -> None: ...
