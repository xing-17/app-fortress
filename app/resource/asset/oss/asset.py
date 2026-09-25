from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.prefix import IPrefix
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.identity.aliyun.aliyun import AliyunIdentity


class OSSAsset(BaseAsset):
    """
    OSS asset contains a collection of OSS assetfiles.

    Args:
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        prefix (str): OSS bucket前缀(默认空字符串)
        identity (AliyunIdentity | str | None): OSS 身份认证
        filesystem (Literal[AssetFilesystem.OSS]): 固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]): 固定为Platform.ALIYUN
        tags (dict[str, str]): OSS asset标签

    """

    # Inherited from BaseAsset
    # - filekind (AssetFileKind): Asset file kind, default is AssetFileKind.OBJECT
    # - partitions (list[str]): Partition keys for the asset
    # - tags (dict[str, str]): Asset tags
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket名称",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket所在区域",
    )
    prefix: str = Field(
        default="",
        description="[Optional] OSS bucket前缀",
    )
    identity: AliyunIdentity | str | None = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] OSS 身份认证",
    )
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSAsset":
        _p = IPrefix.resolve(self.prefix)
        object.__setattr__(self, "prefix", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSAsset":
        _value: AliyunIdentity | str | None = self.identity
        _identity: AliyunIdentity = GlobalIdentities.resolve(
            value=_value,
            platform=Platform.ALIYUN,
            default=AliyunIdentity.default(),
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @property
    def frn(self) -> str:
        return f"asset:{self.platform}:{self.bucket}/{self.prefix}"
