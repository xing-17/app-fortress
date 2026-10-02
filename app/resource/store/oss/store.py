from __future__ import annotations

from pathlib import PurePosixPath
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._base import BaseStore
from app.setting._identity import AbstractIdentitySetting
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
        identity (AliyunIdentity | AbstractIdentitySetting | str | None): Aliyun身份(默认AliyunIdentity.default())
        storesystem (Literal[StoreSystem.OSS]): Store system类型(固定为StoreSystem.OSS)
        platform (Literal[Platform.ALIYUN]): Store platform类型(固定为Platform.ALIYUN)
        tags (dict[str, str]): Store标签

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。

    Methods:
        from_setting(cls, setting: OSSStoreSetting) -> OSSStore:
            Create an OSSStore instance from an OSSStoreSetting object.
        write_bytes(key: str, data: bytes) -> None:
            Write raw bytes to key (relative to prefix).
        read_bytes(key: str) -> bytes:
            Read raw bytes from key (relative to prefix); raises FileNotFoundError if missing.

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
    identity: AliyunIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Identity used for this Aliyun store",
    )

    # Class-level attributes
    default_prefix: ClassVar[str] = "store"

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSStore":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSStore":
        _p = IPrefix.resolve(
            value=self.prefix,
            default=self.default_prefix,
        )
        object.__setattr__(self, "prefix", _p)
        return self

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @property
    def client(self) -> OSSClient:
        return OSSClient.get_client(
            bucket=self.bucket,
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

    def _resolve_key(self, key: str) -> str:
        return str(PurePosixPath(self.prefix) / key)

    def write_bytes(
        self,
        key: str,
        data: bytes,
    ) -> None:
        _key: str = self._resolve_key(key)
        self.client.write_bytes(_key, data)

    def read_bytes(
        self,
        key: str,
    ) -> bytes:
        _key: str = self._resolve_key(key)
        return self.client.read_bytes(_key)

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
            identity=setting.identity,
            tags=setting.tags,
        )
