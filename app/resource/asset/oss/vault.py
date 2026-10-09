from __future__ import annotations

import posixpath
from typing import ClassVar

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.prefix import IPrefix
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._vault import BaseVault
from app.resource.asset.oss.asset import OSSAsset
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.setting._identity import AbstractIdentitySetting
from app.setting._vault import OSSVaultSetting


class OSSVault(BaseVault):
    """
    OSS vault，表示一组OSS asset及其关联assetfile的集合。

    Args:
    ----------
        name (str | None):
            Vault名称
        bucket (str):
            OSS bucket名称
        region (str):
            OSS bucket所在区域
        prefix (str):
            OSS bucket前缀，默认空字符串
        in_vpc (bool):
            是否在VPC内访问OSS，默认False
        identity (AliyunIdentity | AbstractIdentitySetting | str | None):
            Aliyun身份认证，默认AliyunIdentity.default()
        filesystem (Literal[AssetFilesystem.OSS]):
            固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]):
            固定为Platform.ALIYUN
        description (str):
            Vault描述信息
        tags (dict[str, str]):
            Vault标签

    Methods:
    ----------
        from_setting(cls, setting: OSSVaultSetting) -> OSSVault:
            根据OSSVaultSetting对象创建OSSVault实例。
        asset(rel, filekind=None, partitions=None) -> OSSAsset:
            创建一个OSSAsset，其key由vault的prefix与rel拼接而成。

    Example:
    ----------
        >>> from app.resource.asset.oss.vault import OSSVault
        >>> from app.setting._vault import OSSVaultSetting
        >>> setting = OSSVaultSetting(name="my_vault", bucket="my-bucket", region="cn-hangzhou")
        >>> vault = OSSVault.from_setting(setting)

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.OSS
    platform: ClassVar[Platform] = Platform.ALIYUN
    default_prefix: ClassVar[str] = "vault"

    # Enforced instance variables
    # [Inherited] name: str | None
    # [Inherited] description: str
    # [Inherited] tags: dict[str, str]
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
        return IFrn.resolve(
            [
                "vault",
                f"platform={self.platform}",
                f"bucket={self.bucket}",
                f"prefix={self.prefix}",
            ]
        )

    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> "OSSAsset":
        # OSS key 是不透明字符串，存储层不解析 ".."
        # 不存在 LocalVault 那种路径穿越风险，无需 escape 校验
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
            _authorized=True,
        )
