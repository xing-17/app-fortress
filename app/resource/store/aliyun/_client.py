from __future__ import annotations

import threading

from alibabacloud_credentials.models import CredentialModel
from tablestore import OTSClient as OTSTeaClient

from app.resource.identity.aliyun.aliyun import AliyunIdentity


class OTSClient:
    """
    Aliyun OTS Tea SDK 客户端封装。

    Args:
        endpoint (str): 访问该OTS实例的Endpoint URL
        region (str): OTS实例所在的地域
        instance (str): OTS实例名称
        identity (AliyunIdentity): 用于访问该OTS实例的身份信息

    Attributes:
        client (OTSTeaClient): 懒加载并缓存的OTS客户端实例，凭证按需实时获取以支持刷新。

    """

    def __init__(
        self,
        endpoint: str,
        region: str,
        instance: str,
        identity: AliyunIdentity,
    ) -> None:
        self.endpoint: str = endpoint
        self.region: str = region
        self.instance: str = instance
        self.identity: AliyunIdentity = identity
        self._client: OTSTeaClient | None = None
        self._client_lock: threading.RLock = threading.RLock()

    @property
    def client(self) -> OTSTeaClient:
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    _cred: CredentialModel = self.identity.get_credential()
                    self._client = OTSTeaClient(
                        end_point=self.endpoint,
                        access_key_id=_cred.access_key_id,
                        access_key_secret=_cred.access_key_secret,
                        region=self.region,
                        instance_name=self.instance,
                    )
        return self._client
