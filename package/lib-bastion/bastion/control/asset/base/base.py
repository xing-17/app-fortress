from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetkind import AssetKind
from bastion.domain.assetref import BaseAssetRefModel
from bastion.domain.platform import Platform


@runtime_checkable
class IAssetRefLike(Protocol):
    """
    Protocol for asset reference objects.

    Attributes:
        location: Reference location identifier.
        partitions: Partition key-value pairs.
        metadata: Arbitrary metadata.
        tags: Tag key-value pairs.

    Methods:
        from_dict: Create from dictionary.
        from_domain: Create from domain model.
        describe: Get human-readable description.
        export: Export to dictionary.
    """

    location: str
    partitions: dict[str, str]
    metadata: dict[str, Any]
    tags: dict[str, str]

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
    Protocol for asset control objects.

    Attributes:
        domain: Underlying domain model.
        name: Asset name.
        kind: Asset kind (parquet, csv, etc.).
        platform: Storage platform.
        partitions: Partition column names.
        refs: Asset references.
        description: Optional description.
        owner: Optional owner identifier.
        metadata: Arbitrary metadata.
        tags: Tag key-value pairs.
        sha256: Content hash.

    Methods:
        from_dict: Create from dictionary.
        from_domain: Create from domain model.
        get_uri: Get asset URI.
        get_glob: Get glob pattern.
        inspect: Display asset details.
        export: Export to dictionary.
        describe: Get human-readable description.
    
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

    def get_uri(self) -> str: ...

    def get_glob(self) -> str: ...

    def inspect(self) -> None: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> dict[str, Any]: ...
