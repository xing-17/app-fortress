from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion.internal.iclock import IClock
from bastion.internal.idomain import IDomain


class AbstractAssetObjectDomain(
    IDomain,
    ABC,
):
    """
    Abstract base class for logical data assets across platforms.

    Attributes:
        uri (str): Physical URI of the asset component (e.g., 's3://bucket/path/file.parquet').
        size (int | None): Size of the asset reference in bytes
        modified_at (datetime | None): Last modified timestamp of this asset component.
        partitions (dict[str, str]): Partition information for this asset component.
        metadata (dict[str, Any]): Additional metadata associated with the asset reference.

    Methods:
        from_dict(dict data): Create instance from dictionary data.
        export(): Export the underlying domain model to a dictionary.
        describe(): Return a JSON string representation of the domain model.
        clone(**updates): Create a deep copy with updates (inherited).

    """

    _id_enabled: ClassVar[bool] = False
    uri: str = Field(
        ...,
        description="Physical URI of the asset component (e.g., 's3://bucket/path/file.parquet').",
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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata associated with the asset reference.",
    )

    @field_validator("modified_at", mode="before")
    @classmethod
    def _coerce_optional_datetime(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            return IClock.from_iso(v)
        if isinstance(v, datetime):
            return IClock.from_datetime(v)
        return v
