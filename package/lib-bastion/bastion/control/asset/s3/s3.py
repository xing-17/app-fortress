from __future__ import annotations

import logging

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset.base import BaseAssetModel

logger = logging.getLogger(__name__)


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


class S3Asset(
    IBastionObject,
    IAssetLike,
):
    _domain_class: type[S3AssetModel] = S3AssetModel

    def get_location_uri(self) -> str:
        _bucket = self.domain.bucket
        _prefix = self.domain.prefix.lstrip("/")
        return f"s3://{_bucket}/{_prefix}"
