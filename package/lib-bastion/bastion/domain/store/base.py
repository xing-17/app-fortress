from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class StoreKind(StrEnum):
    MEMORY = "memory"


class BaseStoreModel(IBastionModel):
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
