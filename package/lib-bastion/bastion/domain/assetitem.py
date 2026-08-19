from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import Field

from bastion._internal.model import IBastionModel
from bastion.domain.platform import Platform


class BaseAssetItemModel(
    IBastionModel,
    ABC,
):
    name: str = Field(
        ...,
        description="Name of the asset item",
    )
    platform: Platform = Field(
        Platform.LOCAL,
        description="Platform of the asset",
    )
    partitions: dict[str, str] = Field(
        default_factory=dict,
        description="Partitions of the asset item",
    )
    owner: str | None = Field(
        default=None,
        description="Owner of the asset item",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata associated with the asset item",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the asset",
    )
