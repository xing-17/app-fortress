from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar
from datetime import datetime
from pathlib import Path

from pydantic import Field, computed_field

from bastion._internal.model import IBastionModel


class BaseAssetRefModel(
    IBastionModel,
    ABC,
):
    _id_enabled: ClassVar[bool] = False
    uri: str = Field(
        ...,
        description="Physical uri of asset component (e.g., 's3://bucket/path/file.parquet').",
    )
    size: int | None = Field(
        default=None,
        description="Size of the asset reference in bytes",
    )
    modified_at: datetime | None = Field(
        default=None,
        description="Last modified timestamp of this asset component.",
    )
    partitions: dict[str, str] = Field(
        default_factory=dict,
        description="Partition information for this asset component.",
    )
