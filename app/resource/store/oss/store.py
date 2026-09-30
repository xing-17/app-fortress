from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.prefix import IPrefix
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._base import BaseStore
from app.setting._store import OSSStoreSetting


class OSSStore(BaseStore):
    """
    OSS store backed by Aliyun Object Storage Service.

    Args:
        name (str): Store name
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        prefix (str | None): OSS bucket前缀(默认store)
        in_vpc (bool): 是否在VPC内访问OSS(默认False)
        identity (AliyunIdentity): Aliyun身份(默认AliyunIdentity.default())
        storesystem (Literal[StoreSystem.OSS]): Store system类型(固定为StoreSystem.OSS)
        platform (Literal[Platform.ALIYUN]): Store platform类型(固定为Platform.ALIYUN)
        tags (dict[str, str]): Store标签

    Methods:
        from_setting(cls, setting: OSSStoreSetting) -> OSSStore:
            Create an OSSStore instance from an OSSStoreSetting object.

    Example:
        >>> from app.resource.store.oss.store import OSSStore
        >>> store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        >>> store.uri
        'oss://my-bucket/store'

    """

    # Inherited from BaseStore
    # - name: str
    # - tags: dict[str, Any]
    storesystem: Literal[StoreSystem.OSS] = StoreSystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket name",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket所在区域",
    )
    prefix: str | None = Field(
        default=None,
        description="[Optional] OSS bucket前缀",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] Identity used for this Aliyun store",
    )

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSStore":
        if not self.prefix:
            _p = "store"
        else:
            _p = IPrefix.resolve(self.prefix)
        object.__setattr__(self, "prefix", _p)
        return self

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @classmethod
    def from_setting(
        cls,
        setting: OSSStoreSetting,
    ) -> OSSStore:
        return cls(
            name=setting.name,
            bucket=setting.bucket,
            region=setting.region,
            prefix=setting.prefix,
            in_vpc=setting.in_vpc,
            identity=GlobalIdentities.resolve(
                value=getattr(setting, "identity", None),
                platform=Platform.ALIYUN,
                default=AliyunIdentity.default(),
            ),
            tags=setting.tags,
        )
