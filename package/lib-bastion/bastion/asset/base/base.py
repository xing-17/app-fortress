from __future__ import annotations

from typing import Any, ClassVar, Protocol

from pydantic import Field

from bastion._internal.model import IBastionModel


class AssetLike(Protocol):
    """
    Structural protocol

    Core attributes:
        id: Unique identifier for the asset
        name: Human-readable name for the asset
        description: Optional description of the asset
        metadata: Arbitrary key-value metadata associated with the asset
        tags: List of tags associated with the asset

    """

    id: str
    name: str
    description: str | None
    owner: str | None
    metadata: dict[str, Any]
    tags: dict[str, str]


class BaseAsset(IBastionModel):
    """
    Base Asset model.

    Subclasses represent a concrete storage backend (S3, Redshift, local ...)
    and SHOULD set ``kind`` to its identifier.

    """

    _id_prefix: ClassVar[str] = "asset"
    _id_length: ClassVar[int] = 12

    name: str
    description: str | None = None
    owner: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
