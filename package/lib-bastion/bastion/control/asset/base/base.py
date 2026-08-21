from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetkind import AssetKind
from bastion.domain.assetref import BaseAssetRefModel
from bastion.domain.platform import Platform


@runtime_checkable
class IAssetRefLike(Protocol):
    """
    Represents a single file or object within an asset.

    An asset reference points to an actual file (e.g., a parquet file) and includes
    metadata like size, timestamps, and partition values.

    Attributes:
        uri: Full path or URL to the file
        partitions: Partition values extracted from the path (e.g., {"year": "2024", "month": "01"})
        size: File size in bytes (None if unknown)
        created_at: When the file was created (None if unknown)
        updated_at: When the file was last modified (None if unknown)

    Methods:
        from_dict: Create a reference from a dictionary
        from_domain: Create a reference from a domain model
        describe: Get a human-readable summary of the reference
        export: Convert the reference to a dictionary
    """

    uri: str
    size: int | None
    created_at: datetime | None
    updated_at: datetime | None
    partitions: dict[str, str]

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IAssetRefLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: BaseAssetRefModel,
    ) -> IAssetRefLike: ...

    def describe(self) -> dict[str, Any]: ...

    def export(self) -> dict[str, Any]: ...


@runtime_checkable
class IAssetLike(Protocol):
    """
    Represents a logical data asset that may consist of multiple files.

    An asset is a collection of files organized by name, type, and optionally partitions.
    For example, a sales dataset partitioned by year and month.

    Attributes:
        domain: The underlying domain model containing core data
        name: Unique identifier for this asset
        kind: File format (parquet, csv, json, etc.)
        platform: Where the data lives (local, s3, azure, etc.)
        partitions: List of partition column names (e.g., ["year", "month"])
        refs: List of actual files belonging to this asset
        description: Human-readable description of the asset
        owner: Who owns or manages this asset
        metadata: Custom key-value pairs for additional information
        tags: Classification tags for organization
        sha256: Content hash for data integrity

    Methods:
        from_dict: Create an asset from a dictionary
        from_domain: Create an asset from a domain model
        inspect: Scan storage and discover all files in this asset
        export: Convert the asset to a dictionary
        describe: Get a human-readable summary of the asset

    """

    domain: BaseAssetModel
    name: str
    kind: AssetKind
    platform: Platform
    partitions: list[str] | None
    refs: list[IAssetRefLike] | None
    description: str | None
    owner: str | None
    metadata: dict[str, Any]
    tags: dict[str, str]
    sha256: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IAssetLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: BaseAssetModel,
    ) -> IAssetLike: ...

    def inspect(self) -> None: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> dict[str, Any]: ...
