from __future__ import annotations

import logging
import threading
from typing import Any, Literal

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
        name (str):
            Name of the Aliyun OTS store.
        instance (str):
            Instance name of the Aliyun OTS store.
        region (str):
            Region of the Aliyun OTS store.
        in_vpc (bool):
            Whether the store is within a VPC.
        endpoint (str | None):
            Endpoint URL for the store.
        identity (AliyunIdentity):
            Identity used for the store.
        tags (dict[str, Any] | None):
            Tags associated with the store.

    Attributes:
        client (OTSClient):
            Cached OTS client instance.

    Methods:
        from_setting(setting: AliyunStoreSetting) -> "OtsStore":
            Creates an OtsStore instance from the given AliyunStoreSetting.
        instance_exists() -> bool:
            Checks if the Aliyun OTS instance exists.
        describe() -> str:
            Returns a JSON-formatted string describing the store.
        export() -> dict[str, Any]:
            Returns a dictionary containing the store's details.

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
        description="Instance name of the Aliyun OTS store",
    )
    region: str = Field(
        ...,
        description="Region of this Aliyun store",
    )
    in_vpc: bool = Field(
        False,
        description="Whether the Aliyun store is within a VPC",
    )
    endpoint: str | None = Field(
        default=None,
        description="Endpoint URL for this Aliyun store",
    )
    identity: AliyunIdentity = Field(
        default_factory=AliyunIdentity.default,
        description="Identity used for this Aliyun store",
    )

    # Cached private attributes
    _client: OTSClient | None = PrivateAttr(default=None)
    _client_lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_endpoint(self) -> "OtsStore":
        if self.endpoint is None:
            _svc: str = "ots-internal" if self.in_vpc else "ots"
            self.endpoint = f"https://{self.instance}.{self.region}.{_svc}.aliyuncs.com"
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
            identity=GlobalIdentities.get_identity(
                name=getattr(setting, "identity", None),
                strict=False,
            )
            or AliyunIdentity.default(),
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

    def instance_exists(self) -> bool:
        try:
            self.client.list_table()
        except (MaxRetryError, NameResolutionError):
            return False
        return True

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = self.identity.name
        return _res
