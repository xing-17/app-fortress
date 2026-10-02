from __future__ import annotations

import posixpath
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.prefix import IPrefix
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._vault import BaseVault
from app.resource.asset.oss.asset import OSSAsset
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.setting._identity import AbstractIdentitySetting
from app.setting._vault import OSSVaultSetting


class OSSVault(BaseVault):
    """
    OSS Vault Connection

    Args:
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        name (str | None): Vault名称
        prefix (str): OSS bucket前缀(默认空字符串)
        in_vpc (bool): 是否在VPC内访问OSS (默认False)
        identity (AliyunIdentity | AbstractIdentitySetting | str | None): Aliyun身份(默认AliyunIdentity.default())
        filesystem (Literal[AssetFilesystem.OSS]): 文件系统类型(固定为AssetFilesystem.OSS)
        platform (Literal[Platform.ALIYUN]): 平台类型(固定为Platform.ALIYUN)
        description (str): Vault描述信息
        tags (dict[str, str]): Vault标签

    Methods:
        from_setting(cls, setting: OSSVaultSetting) -> OSSVault:
            Create an OSSVault instance from an OSSVaultSetting object.
        asset(rel, filekind=None, partitions=None) -> OSSAsset:
            Create an OSSAsset scoped to a key joined from the vault prefix and rel.

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
    prefix: str | None = Field(
        default=None,
        description="[Optional] OSS bucket前缀, 默认为/vault",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Aliyun Identity身份认证",
    )

    # Class-level attributes
    default_prefix: ClassVar[str] = "vault"

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSVault":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSVault":
        _p = IPrefix.resolve(
            value=self.prefix,
            default=self.default_prefix,
        )
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
            in_vpc=setting.in_vpc,
            identity=setting.identity,
            description=setting.description,
            tags=setting.tags,
        )

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @property
    def frn(self) -> str:
        return f"vault:{self.platform}:{self.bucket}/{self.prefix}"

    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> "OSSAsset":
        _seg: str = rel.strip("/")
        _key: str = posixpath.join(self.prefix, _seg)
        return OSSAsset(
            bucket=self.bucket,
            region=self.region,
            prefix=_key,
            filekind=filekind,
            in_vpc=self.in_vpc,
            partitions=partitions,
            identity=self.identity,
            tags=self.tags,
        )
