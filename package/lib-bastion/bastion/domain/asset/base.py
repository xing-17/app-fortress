from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class AssetKind(StrEnum):
    PARQUET = "parquet"
    CSV = "csv"

    @classmethod
    def from_any(
        cls,
        value: str | AssetKind,
    ) -> AssetKind:
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid AssetKind value: {value}")

    def __str__(self) -> str:
        return self.value


class AssetPlatform(StrEnum):
    S3 = "s3"
    LOCAL = "local"
    OSS = "oss"

    @classmethod
    def from_any(
        cls,
        value: str | AssetPlatform,
    ) -> AssetPlatform:
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid AssetPlatform value: {value}")

    def __str__(self) -> str:
        return self.value


class BaseAssetModel(IBastionModel, ABC):
    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the asset",
    )
    kind: AssetKind = Field(
        ...,
        description="Kind of the asset",
    )
    platform: AssetPlatform = Field(
        ...,
        description="Platform of the asset",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the asset",
    )
    owner: str | None = Field(
        default=None,
        description="Owner of the asset",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata associated with the asset",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the asset",
    )

    @abstractmethod
    def get_location_uri(self) -> str: ...

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "platform": self.platform.value,
            "description": self.description,
            "owner": self.owner,
            "metadata": self.metadata,
            "tags": self.tags,
        }
