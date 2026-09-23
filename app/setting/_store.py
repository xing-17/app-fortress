from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.platform import Platform


class AbstractStoreSetting(IAbstractTaggedSetting):
    """
    Abstract store setting

    Attributes:
        name (str): Store name
        platform (Platform): Store platform
        tags (dict[str, str]): Store tags

    """

    name: str = Field(
        ...,
        description="[Required] Store name",
    )
    platform: Platform = Field(
        ...,
        description="[discriminator] Store platform",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Store tags",
    )

    @property
    def frn(self) -> str:
        return f"setting:store:platform={self.platform}:name={self.name}"

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "name": self.name,
        }


class LocalStoreSetting(AbstractStoreSetting):
    """
    Local store setting

    Attributes:
        name (str): Store name
        platform (Platform): Store platform
        identity (str | None): Local store identity
        path (str | None): Local store path
        config (dict[str, Any] | None): Local store configuration
        tags (dict[str, str]): Store tags

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- platform: Platform
    # -- tags: dict[str, str]
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    path: str | None = Field(
        default=None,
        description="[Optional] Local store path",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="[Optional] Local store configuration",
    )
    identity: str | None = Field(
        default=None,
        description="[Optional] Local store identity",
    )


class AliyunStoreSetting(AbstractStoreSetting):
    """
    阿里云存储设置

    Attributes:
        name (str): 阿里云存储数据库名称
        platform (Platform): 存储平台
        instance (str): 阿里云OTS实例名称
        region (str): 阿里云region
        in_vpc (bool): 存储是否处于VPC内
        endpoint (str | None): 存储的Endpoint地址
        identity (str | None): 存储所使用的Identity名称
        tags (dict[str, str]): 存储标签

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- tags: dict[str, str]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    instance: str = Field(
        ...,
        description="[Required] 阿里云OTS实例名称",
    )
    region: str = Field(
        ...,
        description="[Required] 阿里云region",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 存储是否处于VPC内",
    )
    endpoint: str | None = Field(
        default=None,
        description="[Optional] 存储的Endpoint地址",
    )
    identity: str | None = Field(
        default=None,
        description="[Optional] 存储所使用的Identity名称",
    )


UnionStoreSetting = Annotated[
    Union[
        LocalStoreSetting,
        AliyunStoreSetting,
    ],
    Field(discriminator="platform"),
]
