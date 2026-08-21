from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform
from bastion.domain.assetref import BaseAssetRefModel


class BaseAssetModel(
    IBastionModel,
    ABC,
):
    """
    Abstract base class for all data asset models representing logical data assets across platforms.

    Attributes:
        name (str): Name of the asset.
        kind (AssetKind): Kind of the asset (e.g., parquet, csv, any).
        platform (Platform): Platform where the asset is stored (local, s3, oss).
        partitions (list[str]): List of partition keys for the asset.
        description (str | None): Optional description of the asset.
        owner (str | None): Optional owner of the asset.
        metadata (dict[str, Any]): Additional metadata associated with the asset.
        tags (dict[str, str]): Tags associated with the asset.
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        from_any(value): Convert dict or instance to asset model (inherited).
        export(): Export asset information to a dictionary.
        describe(): Export asset as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        asset = BaseAssetModel(
            name="data-asset",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month"],
            description="Asset for data processing",
            owner="data-team",
            metadata={"priority": "high"},
            tags={"env": "prod"}
        )
        data = asset.export()
        ```
    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the asset",
    )
    kind: AssetKind = Field(
        ...,
        description="Kind of the asset",
    )
    platform: Platform = Field(
        Platform.LOCAL,
        description="Platform of the asset",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys for the asset",
    )
    refs: list[BaseAssetRefModel] = Field(
        default_factory=list,
        description="List of asset references (components) for the asset",
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
