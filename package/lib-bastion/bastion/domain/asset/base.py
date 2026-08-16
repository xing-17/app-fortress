from __future__ import annotations

from abc import ABC
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class AssetKind(StrEnum):
    """
    Enumeration of supported asset file formats.

    Attributes:
        PARQUET (str): Parquet columnar storage format.
        CSV (str): Comma-separated values format.

    Methods:
        from_any(str | AssetKind value): Convert string or enum to AssetKind.

    Example:
        ```python
            # Create from string
            kind = AssetKind.from_any("parquet")

            # Create from enum
            kind = AssetKind.from_any(AssetKind.CSV)

            # Use directly
            kind = AssetKind.PARQUET
        ```
    """

    PARQUET = "parquet"
    CSV = "csv"


class AssetPlatform(StrEnum):
    """
    Enumeration of supported storage platforms for assets.

    Attributes:
        S3 (str): Amazon S3 cloud storage.
        LOCAL (str): Local file system storage.
        OSS (str): Alibaba Cloud Object Storage Service.

    Methods:
        from_any(str | AssetPlatform value): Convert string or enum to AssetPlatform.

    Example:
        ```python
            # Create from string
            platform = AssetPlatform.from_any("s3")

            # Create from enum
            platform = AssetPlatform.from_any(AssetPlatform.LOCAL)

            # Use directly
            platform = AssetPlatform.OSS
        ```
    """

    S3 = "s3"
    LOCAL = "local"
    OSS = "oss"


class BaseAssetModel(IBastionModel, ABC):
    """
    Abstract base class for all data asset models representing logical data assets across platforms.

    Attributes:
        name (str): Name of the asset.
        kind (AssetKind): Kind of the asset (e.g., parquet, csv).
        platform (AssetPlatform): Platform where the asset is stored (s3, local, oss).
        description (str | None): Optional description of the asset.
        owner (str | None): Owner of the asset.
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
            platform=AssetPlatform.S3,
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
