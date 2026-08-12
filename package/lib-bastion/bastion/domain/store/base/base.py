from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Protocol, runtime_checkable

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseStoreModel(IBastionModel):
    _id_prefix: ClassVar[str] = "store"
    _id_length: ClassVar[int] = 12
    name: str = Field(
        ...,
        description="Name of the store",
    )
    kind: str = Field(
        ...,
        description="Kind of the store (e.g., S3, Redshift, local)",
    )

    @property
    def identifier(self) -> str:
        return f"{self.kind}:{self.name}"
