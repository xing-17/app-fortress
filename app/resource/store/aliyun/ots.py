from __future__ import annotations

import logging
import threading
from typing import Literal

logging.getLogger("tablestore").setLevel(logging.ERROR)

from alibabacloud_credentials.models import CredentialModel
from pydantic import Field, PrivateAttr, model_validator
from tablestore import OTSClient
from urllib3.exceptions import MaxRetryError, NameResolutionError

from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._base import BaseStore
from app.setting._store import AliyunStoreSetting


class OtsStore(BaseStore):
    """
    Aliyun OTS store resource.

    Args:
        name (str): 自定义名称,
        instance (str): OTS实例名称
        region (str): OTS实例所在的地域
        in_vpc (bool): 是否在VPC内。
        endpoint (str | None): 访问该OTS实例的Endpoint URL。
        identity (AliyunIdentity): 用于访问该OTS实例的身份信息。
        tags (dict[str, Any] | None): 与该OTS实例相关的标签。

    Attributes:
        client (OTSClient): 缓存的OTS客户端实例。

    Methods:
        from_setting(setting: AliyunStoreSetting) -> "OtsStore":
            从给定的AliyunStoreSetting创建一个OtsStore实例。
        instance_exists() -> bool:
            检查Aliyun OTS实例是否存在。
        describe() -> str:
            返回描述该存储的JSON格式字符串。
        export() -> dict[str, Any]:
            返回包含该存储详细信息的字典。

    Examples:
        >>> store = OtsStore(
        ...     name="my-ots-store",
        ...     instance="my-instance",
        ...     region="cn-hangzhou",
        ...     in_vpc=False,
        ...     identity=AliyunIdentity.default(),
        ... )
        >>> store.describe()
        >>> store.client  # Access the cached OTS client instance

    """

    # Inherited from BaseStore
    # - name: str
    # - tags: dict[str, Any]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    instance: str = Field(
        ...,
        description="[Required] Instance name of the Aliyun OTS store",
    )
    region: str = Field(
        ...,
        description="[Required] Region of this Aliyun store",
    )
    in_vpc: bool = Field(
        False,
        description="[Optional] Whether the Aliyun store is within a VPC",
    )
    endpoint: str | None = Field(
        default=None,
        description="[Optional] Endpoint URL for this Aliyun store",
    )
    identity: AliyunIdentity = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] Identity used for this Aliyun store",
    )

    # Cached private attributes
    _client: OTSClient | None = PrivateAttr(default=None)
    _client_lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_endpoint(self) -> "OtsStore":
        if self.endpoint in (None, ""):
            # Derive the endpoint URL if it is not explicitly provided.
            _svc: str = "ots-internal" if self.in_vpc else "ots"
            _ep = f"https://{self.instance}.{self.region}.{_svc}.aliyuncs.com"
            object.__setattr__(self, "endpoint", _ep)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: AliyunStoreSetting,
    ) -> "OtsStore":
        return cls(
            name=setting.name,
            instance=setting.instance,
            region=setting.region,
            in_vpc=setting.in_vpc,
            endpoint=setting.endpoint,
            identity=GlobalIdentities.resolve(
                value=getattr(setting, "identity", None),
                platform=Platform.ALIYUN,
                default=AliyunIdentity.default(),
            ),
            tags=setting.tags,
        )

    @property
    def client(self) -> OTSClient:
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    _cred: CredentialModel = self.identity.get_credential()
                    self._client = OTSClient(
                        end_point=self.endpoint,
                        access_key_id=_cred.access_key_id,
                        access_key_secret=_cred.access_key_secret,
                        region=self.region,
                        instance_name=self.instance,
                    )
        return self._client

    @property
    def frn(self) -> str:
        return f"store:aliyun:{self.name}"

    def instance_exists(self) -> bool:
        try:
            self.client.list_table()
        except (MaxRetryError, NameResolutionError):
            return False
        return True
