from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import Field

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.resource.identity._common._identity import BaseIdentity
from app.resource.store._common._base import GovernedStoreResource
from app.resource.store._common._table import BaseTable
from app.setting._identity import AbstractIdentitySetting


class BaseDatabase(
    GovernedStoreResource,
    ABC,
):
    """
    Base class for store database resources, governed and derived from a parent.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system
        platform (Platform):
            Store platform

    Args:
    ----------
        name (str):
            Database name
        identity (BaseIdentity | AbstractIdentitySetting | str | None):
            Database identity
        tags (dict[str, str]):
            Database tags

    Methods:
    ----------
        list_tables() -> list[BaseTable]:
            Enumerate tables that currently exist under this database.
        table(name: str, ttl_hours: float | None = None) -> BaseTable:
            Only entry point for building a table under this database.
        delete(name: str, strict: bool = False) -> None:
            Delete a table under this database; raises if missing and strict is True.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem]
    platform: ClassVar[Platform]

    # Enforced instance variables
    # [Inherited] tags: dict[str, str]
    name: str = Field(
        ...,
        description="[Required] Database name, single path segment governed by the parent store",
    )
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Database identity",
    )

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

    @abstractmethod
    def list_tables(self) -> list[BaseTable]: ...

    @abstractmethod
    def table(
        self,
        name: str,
        ttl_hours: float | None = None,
    ) -> BaseTable: ...

    @abstractmethod
    def delete(
        self,
        name: str,
        strict: bool = False,
    ) -> None: ...
