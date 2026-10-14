from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.setting._identity import (
    AbstractIdentitySetting,
    AliyunIdentitySetting,
    LocalIdentitySetting,
)

STORE_NAME_PATTERN: str = r"^[A-Za-z0-9_]+$"


class AbstractStoreSetting(IAbstractTaggedSetting):
    """
    Abstract store setting

    Attributes:
    ----------
        name (str): Store name
        storesystem (StoreSystem): Store system type
        platform (Platform): Store platform
        identity (AbstractIdentitySetting | str | None): Identity configuration or name for the store
        tags (dict[str, str]): Store tags

    """

    name: str = Field(
        ...,
        description="[Required] Store name",
        pattern=STORE_NAME_PATTERN,
    )
    storesystem: StoreSystem = Field(
        ...,
        description="[discriminator] Store system",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Store platform",
    )
    identity: AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] identity for the store",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Store tags",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "setting",
                "store",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "storesystem": self.storesystem,
            "platform": self.platform,
            "name": self.name,
        }


class FileStoreSetting(AbstractStoreSetting):
    """
    File store setting

    Attributes:
    ----------
        name (str): Store name
        storesystem (Literal[StoreSystem.FILE]): fixed as StoreSystem.FILE
        platform (Literal[Platform.LOCAL]): fixed as Platform.LOCAL
        path (str | None): File store path
        identity (LocalIdentitySetting | str | None): File store identity
        tags (dict[str, str]): Store tags

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- storesystem: StoreSystem
    # -- platform: Platform
    # -- tags: dict[str, str]
    storesystem: Literal[StoreSystem.FILE] = StoreSystem.FILE
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    path: str | None = Field(
        default=None,
        description="[Optional] File store path",
    )
    identity: LocalIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] File store identity",
    )


class OSSStoreSetting(AbstractStoreSetting):
    """
    OSS store 配置

    Attributes:
    ----------
        name (str): Store 名称
        storesystem (Literal[StoreSystem.OSS]): 固定为 StoreSystem.OSS
        platform (Literal[Platform.ALIYUN]): 固定为 Platform.ALIYUN
        bucket (str): OSS bucket 名称
        region (str): OSS bucket 所在区域
        prefix (str | None): OSS bucket 前缀
        in_vpc (bool): 是否在 VPC 内访问 OSS
        identity (AliyunIdentitySetting | str | None): OSS store 身份认证
        tags (dict[str, str]): Store 标签

    """

    # Inherited from AbstractStoreSetting
    # -- name: str
    # -- storesystem: StoreSystem
    # -- platform: Platform
    # -- tags: dict[str, str]
    storesystem: Literal[StoreSystem.OSS] = StoreSystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket 名称",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket 所在区域",
    )
    prefix: str | None = Field(
        default=None,
        description="[Optional] OSS bucket 前缀",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在 VPC 内访问 OSS",
    )
    identity: AliyunIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] OSS store 身份认证",
    )


UnionStoreSetting = Annotated[
    Union[
        FileStoreSetting,
        OSSStoreSetting,
    ],
    Field(discriminator="storesystem"),
]
