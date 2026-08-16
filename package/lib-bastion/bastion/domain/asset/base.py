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

    @classmethod
    def from_any(
        cls,
        value: str | AssetKind,
    ) -> AssetKind:
        """
        Convert a string or AssetKind instance to AssetKind enum.

        Accepts both string values and existing enum instances. Raises ValueError
        if the string value is not a valid AssetKind.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid AssetKind value: {value}")


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

    @classmethod
    def from_any(
        cls,
        value: str | AssetPlatform,
    ) -> AssetPlatform:
        """
        Convert a string or AssetPlatform instance to AssetPlatform enum.

        Accepts both string values and existing enum instances. Raises ValueError
        if the string value is not a valid AssetPlatform.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid AssetPlatform value: {value}")


class BaseAssetModel(IBastionModel, ABC):
    """
    Abstract base class for all data asset models.

    Provides common fields and behavior for representing logical data assets
    across different platforms and formats. Subclasses must implement the
    get_location_uri method to specify how to locate the asset.

    Attributes:
        _id_enabled (ClassVar[bool]): Disabled ID auto-generation (uses name as key).
        name (str): Name of the asset.
        kind (AssetKind): Kind of the asset (e.g., parquet, csv).
        platform (AssetPlatform): Platform where the asset is stored.
        description (str | None): Optional description of the asset.
        owner (str | None): Owner of the asset.
        metadata (dict[str, Any]): Additional metadata associated with the asset.
        tags (dict[str, str]): Tags associated with the asset.

    Methods:
        get_location_uri(): Get the full URI location of the asset.
        export(): Export asset information to a dictionary.

    Example:
        ```python
            from bastion.domain.asset import BaseAssetModel, AssetKind, AssetPlatform

            class S3Asset(BaseAssetModel):
                bucket: str
                key: str

                def get_location_uri(self) -> str:
                    return f"s3://{self.bucket}/{self.key}"

            asset = S3Asset(
                name="sales_data",
                kind=AssetKind.PARQUET,
                platform=AssetPlatform.S3,
                bucket="my-bucket",
                key="data/sales.parquet",
                description="Monthly sales data",
                owner="data-team",
                tags={"env": "prod"}
            )
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
