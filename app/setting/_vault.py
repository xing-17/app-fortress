from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform


class AbstractVaultSetting(IAbstractTaggedSetting):
    """
    An asset vault contains a collection of assets and associated assetfile.

    Attributes:
        name (str): Asset vault name
        filesystem (AssetFilesystem): Asset vault filesystem type
        platform (Platform): Asset vault operating platform
        description (str): Asset vault description information
        tags (dict[str, str]): Asset tags

    """

    name: str = Field(
        ...,
        description="[Required] Asset vault name",
    )
    filesystem: AssetFilesystem = Field(
        ...,
        description="[discriminator] Asset filesystem type",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Asset platform type",
    )
    identity: str | None = Field(
        default=None,
        description="[Optional] OSS identity for the asset",
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
        return f"setting:vault:platform={self.platform}:filesystem={self.filesystem}:name={self.name}"

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
        name (str): Asset vault name
        path (str): Local path to a list of assets
        platform (Literal[Platform.LOCAL]): Asset platform type, fixed as LOCAL
        filesystem (Literal[AssetFilesystem.LOCAL]): Asset filesystem type, fixed as LOCAL
        identity (str | None): OSS identity for the asset access
        description (str): Asset description information
        tags (dict[str, str]): Asset vault tags

    """

    # Inherited from AbstractVaultSetting
    # - platform: Platform
    # - filesystem: AssetFilesystem
    # - identity: str | None
    # - description: str
    # - tags: dict[str, str]
    path: str = Field(
        ...,
        description="[Required] Local path to a list of assets",
    )
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    filesystem: Literal[AssetFilesystem.LOCAL] = AssetFilesystem.LOCAL


class OSSVaultSetting(AbstractVaultSetting):
    """
    OSS资产库，包含一组OSS资产及其关联的资产文件。

    Attributes:
        name (str): 资产库名称
        bucket (str): OSS桶名称
        region (str): 资产所在的OSS区域
        prefix (str): 资产的OSS前缀
        identity (str | None): 资产访问所使用的OSS Identity
        platform (Literal[Platform.ALIYUN]): 资产平台类型，固定为ALIYUN
        filesystem (Literal[AssetFilesystem.OSS]): 资产文件系统类型，固定为OSS
        description (str): 资产库描述信息
        tags (dict[str, str]): 资产标签

    """

    # Inherited from AbstractVaultSetting
    # - platform: Platform
    # - filesystem: AssetFilesystem
    # - identity: str | None
    # - description: str | None
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
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS


UnionVaultSetting = Annotated[
    Union[
        LocalVaultSetting,
        OSSVaultSetting,
    ],
    Field(discriminator="filesystem"),
]
