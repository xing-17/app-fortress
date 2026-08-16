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
    Base store model for persistence interface defining storage backend configuration.

    Attributes:
        id (str): Unique identifier (inherited from IBastionModel, disabled for stores).
        name (str): Name of the store.
        kind (StoreKind): Kind of the store (memory, local).
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        from_any(value): Convert dict or instance to store model (inherited).
        identifier: Get the unique identifier combining kind and name (property).
        export(): Export the store as a dictionary.
        describe(): Export store as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        store = BaseStoreModel(
            name="my_store",
            kind=StoreKind.MEMORY,
        )
        data = store.export()
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
