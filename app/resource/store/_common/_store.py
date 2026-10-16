from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import Field

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.resource.identity._common._identity import BaseIdentity
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

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system
        platform (Platform):
            Store platform

    Args:
    ----------
        name (str):
            Store name
        identity (BaseIdentity | AbstractIdentitySetting | str | None):
            Store identity
        tags (dict[str, str]):
            Store tags

    Methods:
    ----------
        from_setting(setting: UnionStoreSetting) -> BaseStore:
            Create a store instance from a setting (base implementation is a stub).
        list_databases() -> list[BaseDatabase]:
            Enumerate databases that currently exist under this store.
        database(name: str) -> BaseDatabase:
            Only entry point for building a database under this store.
        table(database: str, name: str, ttl_hours: float | None = None, max_items: int | None = None) -> BaseTable:
            Only entry point for building a table under a database of this store.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem]
    platform: ClassVar[Platform]

    # Enforced instance variables
    # [Inherited] tags: dict[str, str]
    name: str = Field(
        ...,
        description="[Required] Store name",
    )
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Store identity",
    )

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
        ttl_hours: float | None = None,
        max_items: int | None = None,
    ) -> BaseTable: ...
