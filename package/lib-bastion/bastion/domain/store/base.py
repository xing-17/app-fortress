from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class StoreKind(StrEnum):
    """
    Store kind enumeration for different storage types.

    Attributes:
        MEMORY (str): In-memory storage.
        LOCAL (str): Local DuckDB file storage.

    Methods:
        from_any(value): Convert string or StoreKind to StoreKind instance.

    Example:
        ```python
        kind = StoreKind.MEMORY
        kind_from_str = StoreKind.from_any("memory")
        ```
    """

    MEMORY = "memory"
    LOCAL = "local"


class BaseStoreModel(IBastionModel):
    """
    Base store model for persistence interface.

    Attributes:
        name (str): Name of the store.
        kind (StoreKind): Kind of the store (e.g., memory, S3, Redshift).

    Methods:
        identifier: Get the unique identifier combining kind and name.

    Example:
        ```python
        store = BaseStoreModel(name="my_store", kind=StoreKind.MEMORY)
        print(store.identifier)  # "memory:my_store"
        ```
    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the store",
    )
    kind: StoreKind = Field(
        ...,
        description="Kind of the store (e.g., S3, Redshift, local)",
    )

    @property
    def identifier(self) -> str:
        return f"{self.kind}:{self.name}"

    def export(self) -> dict[str, str]:
        return {
            "name": self.name,
            "identifier": self.identifier,
            "kind": self.kind.value,
        }
