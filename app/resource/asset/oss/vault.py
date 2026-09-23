from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._vault import BaseVault
from app.resource.identity.aliyun import AliyunIdentity
from app.setting._vault import OSSVaultSetting


class OSSVault(BaseVault):
    """
    OSS Vault Connection

    Args:
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        name (str | None): Vault名称
        prefix (str | None): OSS bucket前缀(默认空字符串)
        identity (AliyunIdentity): Aliyun身份(默认AliyunIdentity.default())
        filesystem (Literal[AssetFilesystem.OSS]): 文件系统类型(固定为AssetFilesystem.OSS)
        platform (Literal[Platform.ALIYUN]): 平台类型(固定为Platform.ALIYUN)
        description (str | None): Vault描述信息
        tags (dict[str, str] | None): Vault标签

    """

    # Inherited from BaseVault
    # - name: str | None
    # - description: str
    # - tags: dict[str, str]
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
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
    identity: AliyunIdentity = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] Aliyun Identity身份认证",
    )

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSVault":
        _p = self.prefix or ""
        _p = _p.rstrip("/")
        object.__setattr__(self, "prefix", _p)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: OSSVaultSetting,
    ) -> OSSVault:
        return cls(
            name=setting.name,
            bucket=setting.bucket,
            region=setting.region,
            prefix=setting.prefix,
            identity=GlobalIdentities.resolve(
                value=getattr(setting, "identity", None),
                platform=Platform.ALIYUN,
                default=AliyunIdentity.default(),
            ),
            description=setting.description,
            tags=setting.tags,
        )

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.prefix}"

    @property
    def frn(self) -> str:
        return f"vault:{self.platform}:{self.bucket}/{self.prefix}"
