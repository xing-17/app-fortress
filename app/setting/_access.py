from __future__ import annotations
from typing import Annotated, Literal, Union

from app.internal.abstract.setting import IAbstractSetting
from app.internal.constant.platform import Platform
from app.internal.constant.aliyunaccesstype import AliyunAccessType

from pydantic import Field


class AbstractAccessSetting(IAbstractSetting):
    name: str = Field(
        ...,
        description="Access名称",
    )
    platform: str = Field(
        ...,
        description="Access平台类型",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Access标签",
    )


class AliyunAccessSetting(AbstractAccessSetting):
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    type: AliyunAccessType = Field(
        default=AliyunAccessType.CHAIN,
        description="Aliyun access type",
    )
    access_key_id: str | None = Field(
        default=None,
        description="阿里云Access Key ID",
    )
    osenv_access_key_id: str | None = Field(
        default=None,
        description="阿里云Access Key ID环境变量名",
    )
    access_key_secret: str | None = Field(
        default=None,
        description="阿里云Access Key Secret",
    )
    osenv_access_key_secret: str | None = Field(
        default=None,
        description="阿里云Access Key Secret环境变量名",
    )


class LocalAccessSetting(AbstractAccessSetting):
    platform: Literal[Platform.LOCAL] = Platform.LOCAL


UnionAccessSetting = Annotated[
    Union[
        LocalAccessSetting,
        AliyunAccessSetting,
    ],
    Field(discriminator="platform"),
]
