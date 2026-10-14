from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.setting._identity import (
    AbstractIdentitySetting,
    AliyunIdentitySetting,
    LocalIdentitySetting,
)

VAULT_NAME_PATTERN: str = r"^[A-Za-z0-9_]+$"


class AbstractVaultSetting(IAbstractTaggedSetting):
    """
    An asset vault contains a collection of assets and associated assetfile.

    Attributes:
    ----------
        name (str): Asset vault name
        filesystem (AssetFilesystem): Asset vault filesystem type
        platform (Platform): Asset vault operating platform
        identity (AbstractIdentitySetting | str | None): Identity configuration or name for asset access
        description (str): Asset vault description information
        tags (dict[str, str]): Asset tags

    """

    name: str = Field(
        ...,
        description="[Required] Asset vault name",
        pattern=VAULT_NAME_PATTERN,
    )
    filesystem: AssetFilesystem = Field(
        ...,
        description="[discriminator] Asset filesystem type",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Asset platform type",
    )
    identity: AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] identity for the asset",
    )
    description: str = Field(
        default="",
        description="[Optional] description of the asset vault",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Asset tags",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "setting",
                "vault",
                f"platform={self.platform}",
                f"filesystem={self.filesystem}",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "filesystem": self.filesystem,
            "name": self.name,
        }


class LocalVaultSetting(AbstractVaultSetting):
    """
    Local vault contains a collection of local assets and associated assetfile.

    Attributes:
    ----------
        name (str): Asset vault name
        path (str): Local path to a list of assets
        platform (Literal[Platform.LOCAL]): Asset platform type, fixed as LOCAL
        filesystem (Literal[AssetFilesystem.LOCAL]): Asset filesystem type, fixed as LOCAL
        identity (LocalIdentitySetting | str | None): Local identity for the asset access
        description (str): Asset description information
        tags (dict[str, str]): Asset vault tags

    """

    # Inherited from AbstractVaultSetting
    # - platform: Platform
    # - filesystem: AssetFilesystem
    # - description: str
    # - tags: dict[str, str]
    path: str = Field(
        ...,
        description="[Required] Local path to a list of assets",
    )
    identity: LocalIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Local identity for the asset",
    )
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    filesystem: Literal[AssetFilesystem.LOCAL] = AssetFilesystem.LOCAL


class OSSVaultSetting(AbstractVaultSetting):
    """
    OSS资产库，包含一组OSS资产及其关联的资产文件。

    Attributes:
    ----------
        name (str): 资产库名称
        bucket (str): OSS桶名称
        region (str): 资产所在的OSS区域
        prefix (str): 资产的OSS前缀
        in_vpc (bool): 是否在VPC内访问OSS (默认False)
        identity (AliyunIdentitySetting | str | None): 资产访问所使用的阿里云Identity
        platform (Literal[Platform.ALIYUN]): 资产平台类型，固定为ALIYUN
        filesystem (Literal[AssetFilesystem.OSS]): 资产文件系统类型，固定为OSS
        description (str): 资产库描述信息
        tags (dict[str, str]): 资产标签

    """

    # Inherited from AbstractVaultSetting
    # - platform: Platform
    # - filesystem: AssetFilesystem
    # - description: str
    # - tags: dict[str, str]
    bucket: str = Field(
        ...,
        description="[Required] OSS桶名称",
    )
    region: str = Field(
        ...,
        description="[Required] 资产所在的OSS区域",
    )
    prefix: str = Field(
        default="",
        description="[Optional] 资产的OSS前缀",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] 阿里云身份用于资产访问",
    )
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS


UnionVaultSetting = Annotated[
    Union[
        LocalVaultSetting,
        OSSVaultSetting,
    ],
    Field(discriminator="filesystem"),
]
