from __future__ import annotations

from typing import Any, ClassVar
from pydantic import Field

from bastion._internal.model import IBastionModel


class BaseAssetModel(IBastionModel):
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
