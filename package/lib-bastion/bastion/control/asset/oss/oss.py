from __future__ import annotations

from typing import Any

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel


class OSSAssetModel(BaseAssetModel):
    bucket: str = Field(
        ...,
        description="Name of the OSS bucket",
    )
    prefix: str = Field(
        ...,
        description="Key of the OSS object",
    )
    region: str | None = Field(
        default=None,
        description="Region of the OSS bucket",
    )

    def export(self) -> dict[str, Any]:
        return {
            **super().export(),
            "bucket": self.bucket,
            "prefix": self.prefix,
            "region": self.region,
        }


class OSSAsset(IBastionObject):
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
        self.domain: OSSAssetModel = OSSAssetModel(
            name=name,
            kind=AssetKind.from_any(kind),
            platform=AssetPlatform.OSS,
            bucket=bucket,
            prefix=prefix,
            region=region,
            description=description,
            owner=owner,
            metadata=metadata or {},
            tags=tags or {},
        )

    def get_location_uri(self) -> str:
        return f"oss://{self.domain.bucket}/{self.domain.prefix}"

    def export(self) -> dict[str, Any]:
        return {
            "name": self.domain.name,
            "domain": self.domain.export(),
        }
