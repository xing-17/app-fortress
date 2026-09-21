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
        tags (dict[str, str] | None): Store tags

    """

    name: str = Field(
        ...,
        description="Store name",
    )
    platform: Platform = Field(
        ...,
        description="Store platform",
    )
    tags: dict[str, str] | None = Field(
        default_factory=dict,
        description="Store tags",
    )

    def _frn(self) -> str:
        return f"store:{self.platform}:{self.name}"

    def _tag_base(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "frn": self._frn(),
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
        tags (dict[str, str] | None): Store tags

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- platform: Platform
    # -- tags: dict[str, str]
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    identity: str | None = Field(
        None,
        description="Local store identity",
    )
    path: str | None = Field(
        None,
        description="Local store path",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Local store configuration",
    )


class AliyunStoreSetting(AbstractStoreSetting):
    """
    Aliyun store setting

    Attributes:
        name (str): Name of Aliyun store database
        platform (Platform): Store platform
        instance (str): Instance name of the Aliyun OTS store
        region (str): Aliyun region
        in_vpc (bool): Whether the Aliyun store is within a VPC
        endpoint (str | None): Endpoint URL for this Aliyun store
        identity (str | None): Aliyun store identity
        tags (dict[str, str] | None): Store tags

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- tags: dict[str, str]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    name: str = Field(
        ...,
        description="Name of Aliyun store database",
    )
    instance: str = Field(
        ...,
        description="Instance name of the Aliyun OTS store",
    )
    region: str = Field(
        ...,
        description="Aliyun region",
    )
    in_vpc: bool = Field(
        False,
        description="Whether the Aliyun store is within a VPC",
    )
    endpoint: str | None = Field(
        default=None,
        description="Endpoint URL for this Aliyun store",
    )
    identity: str | None = Field(
        None,
        description="Aliyun store identity",
    )


UnionStoreSetting = Annotated[
    Union[
        LocalStoreSetting,
        AliyunStoreSetting,
    ],
    Field(discriminator="platform"),
]
