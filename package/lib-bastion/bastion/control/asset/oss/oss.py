from __future__ import annotations

import logging

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset.base import BaseAssetModel

logger = logging.getLogger(__name__)


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


class OSSAsset(
    IBastionObject,
    IAssetLike,
):
    _domain_class: type[OSSAssetModel] = OSSAssetModel

    def get_location_uri(self) -> str:
        _bucket = self.domain.bucket
        _prefix = self.domain.prefix.lstrip("/")
        return f"oss://{_bucket}/{_prefix}"
