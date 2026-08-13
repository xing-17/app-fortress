from __future__ import annotations

from typing import Any

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel


class S3AssetModel(BaseAssetModel):
    bucket: str = Field(
        ...,
        description="Name of the S3 bucket",
    )
    prefix: str = Field(
        ...,
        description="Key of the S3 object",
    )
    region: str | None = Field(
        default=None,
        description="Region of the S3 bucket",
    )

    def export(self) -> dict[str, Any]:
        return {
            **super().export(),
            "bucket": self.bucket,
            "prefix": self.prefix,
            "region": self.region,
        }


class S3Asset(IBastionObject):
    def __init__(
        self,
        name: str,
        kind: AssetKind,
        bucket: str,
        prefix: str,
        region: str | None = None,
        description: str | None = None,
        owner: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ):
        super().__init__()
        self.domain: S3AssetModel = S3AssetModel(
            name=name,
            kind=AssetKind.from_any(kind),
            platform=AssetPlatform.S3,
            bucket=bucket,
            prefix=prefix,
            region=region,
            description=description,
            owner=owner,
            metadata=metadata or {},
            tags=tags or {},
        )

    def get_location_uri(self) -> str:
        return f"s3://{self.domain.bucket}/{self.domain.prefix}"

    def export(self) -> dict[str, Any]:
        return {
            "name": self.domain.name,
            "domain": self.domain.export(),
        }
