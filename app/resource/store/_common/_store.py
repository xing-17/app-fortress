from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import Field, PrivateAttr

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.resource.identity._common import BaseIdentity
from app.resource.store._common._base import BaseStoreResource
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._table import BaseTable
from app.setting._identity import AbstractIdentitySetting
from app.setting._store import UnionStoreSetting


class BaseStore(
    BaseStoreResource,
    ABC,
):
    """
    Base class for store resources.

    Store is the top level of the store/database/table hierarchy; it owns zero or more
    databases, each of which in turn owns zero or more tables (the only layer that
    exposes write capability).

    Args:
        name (str): Store name
        storesystem (StoreSystem): Store system
        platform (Platform): Store platform
        identity (BaseIdentity | AbstractIdentitySetting | str | None): Store identity
        tags (dict[str, str]): Store tags

    Attributes:
        databases (list[BaseDatabase]): Lazily loaded and cached list of databases under the store.

    Methods:
        from_setting(setting: UnionStoreSetting) -> BaseStore:
            Create a store instance from a setting (base implementation is a stub).
        database(name: str) -> BaseDatabase:
            Only entry point for building a database under this store.
        list_databases() -> list[BaseDatabase]:
            Enumerate databases that currently exist under this store.
        load_databases(force: bool = False) -> list[BaseDatabase]:
            Load (and cache) the databases list, re-scanning when force is True.
        reset_databases() -> None:
            Clear the cached databases list.

    """

    name: str = Field(
        ...,
        description="[Required] Store name",
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
        description="[Optional] Asset vault identity",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Store tags",
    )

    # List of databases under store
    _databases: list[BaseDatabase] | None = PrivateAttr(default=None)

    @classmethod
    def from_setting(
        cls,
        setting: UnionStoreSetting,
    ) -> BaseStore: ...

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "store",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"name={self.name}",
            ]
        )

    @property
    def databases(self) -> list[BaseDatabase]:
        self.load_databases()
        return self._databases

    def load_databases(
        self,
        force: bool = False,
    ) -> list[BaseDatabase]:
        if force or self._databases is None:
            self._databases = self.list_databases()
        return self._databases

    def reset_databases(self) -> None:
        self._databases = None

    @abstractmethod
    def list_databases(self) -> list[BaseDatabase]: ...

    @abstractmethod
    def database(
        self,
        name: str,
    ) -> BaseDatabase: ...

    @abstractmethod
    def table(
        self,
        database: str,
        name: str,
    ) -> BaseTable: ...
