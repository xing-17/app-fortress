from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform


class AbstractIdentitySetting(IAbstractTaggedSetting):
    """
    抽象Identity设置

    Attributes:
        name (str): Identity名称
        platform (str): Identity平台类型
        tags (dict[str, str]): Identity标签

    """

    name: str = Field(
        ...,
        description="[Required] Identity名称",
    )
    platform: Platform = Field(
        ...,
        description="[discriminator] Identity平台类型",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Identity标签",
    )

    @property
    def frn(self) -> str:
        return f"setting:identity:platform={self.platform}:name={self.name}"

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "name": self.name,
        }


class AliyunIdentitySetting(AbstractIdentitySetting):
    """
    阿里云Identity设置

    Attributes:
        name (str): Identity名称
        type (AliyunIdentityType): 阿里云Identity类型
        access_key_id (str | None): 阿里云Access Key ID
        osenv_access_key_id (str | None): 阿里云Access Key ID环境变量名
        access_key_secret (str | None): 阿里云Access Key Secret
        osenv_access_key_secret (str | None): 阿里云Access Key Secret环境变量名
        region (str | None): 阿里云region
        osenv_region (str | None): 阿里云region环境变量名
        tags (dict[str, str]): Identity标签

    """

    # Inherited from AbstractIdentitySetting
    # -- name: str
    # -- tags: dict[str, str]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    type: AliyunIdentityType = Field(
        default=AliyunIdentityType.CHAIN,
        description="[Optional] 阿里云Identity类型",
    )
    access_key_id: str | None = Field(
        default=None,
        description="[Optional] 阿里云Access Key ID",
    )
    osenv_access_key_id: str | None = Field(
        default=None,
        description="[Optional] 阿里云Access Key ID环境变量名",
    )
    access_key_secret: str | None = Field(
        default=None,
        description="[Optional] 阿里云Access Key Secret",
    )
    osenv_access_key_secret: str | None = Field(
        default=None,
        description="[Optional] 阿里云Access Key Secret环境变量名",
    )
    region: str | None = Field(
        default=None,
        description="[Optional] 阿里云region",
    )
    osenv_region: str | None = Field(
        default=None,
        description="[Optional] 阿里云region环境变量名",
    )


class LocalIdentitySetting(AbstractIdentitySetting):
    """
    Local Identity setting

    Attributes:
        name (str): Identity name
        tags (dict[str, str]): Identity tags

    """

    # Inherited from AbstractIdentitySetting
    # -- name: str
    # -- tags: dict[str, str]
    platform: Literal[Platform.LOCAL] = Platform.LOCAL


UnionIdentitySetting = Annotated[
    Union[
        LocalIdentitySetting,
        AliyunIdentitySetting,
    ],
    Field(discriminator="platform"),
]
