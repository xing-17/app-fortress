from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, ClassVar

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.client import CredentialModel
from alibabacloud_credentials.models import Config as CredentialConfig
from pydantic import Field

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.internal.util.environ import IEnviron
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun.identitysecret import AliyunIdentitySecret
from app.setting._identity import AliyunIdentitySetting


class AliyunIdentity(BaseIdentity):
    """
    Aliyun Identity 身份认证

        ref: https://help.aliyun.com/en/sdk/developer-reference/v2-manage-python-access-credentials

    Attributes:
    ----------
        platform (Platform):
            平台类型，固定为Platform.ALIYUN

    Args:
    ----------
        name (str):
            Access名称，唯一标识一个Aliyun身份实例。
        type (AliyunIdentityType):
            Identity类型(默认'chain')
        access_key_id (str | None):
            阿里云Access Key ID(默认None)
        access_key_secret (str | None):
            阿里云Access Key Secret(默认None)
        region (str | None):
            阿里云地区(默认None)
        tags (dict[str, str]):
            权限标签(默认空字典)

    Methods:
    ----------
        from_setting(cls, settings: AliyunIdentitySetting) -> AliyunIdentity:
            从AliyunIdentitySetting创建AliyunIdentity实例。
        get_credential() -> CredentialModel:
            获取Aliyun身份的凭证信息，底层CredentialClient按身份缓存复用并自行刷新临时凭证。
        as_secret() -> AliyunIdentitySecret:
            实时获取凭证并转换为AliyunSecret，密钥以SecretStr持有，可能访问网络，不要缓存返回值。
        describe() -> str:
            返回Access的描述信息，敏感信息会被掩码。
        sha256() -> str:
            基于未掩码的完整内容计算指纹，不同密钥不会碰撞。

    Example:
    ----------
        >>> aliyun_identity = AliyunIdentity(
        ...     name="my_aliyun_identity",
        ...     type="ak",
        ...     access_key_id="your_access_key_id",
        ...     access_key_secret="your_access_key_secret",
        ...     tags={"env": "production"},
        ... )
        >>> print(aliyun_identity.name)
        my_aliyun_identity

    """

    # Enforced public class variables
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced private class variables
    # 按身份指纹缓存的 CredentialClient，由其自行刷新临时凭证
    _credential_clients: ClassVar[dict[str, CredentialClient]] = {}
    _credential_clients_guard: ClassVar[threading.RLock] = threading.RLock()

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    type: AliyunIdentityType = Field(
        default=AliyunIdentityType.CHAIN,
        description="Aliyun 身份类型",
    )
    access_key_id: str | None = Field(
        default=None,
        description="阿里云 Access Key ID",
    )
    access_key_secret: str | None = Field(
        default=None,
        description="阿里云 Access Key Secret",
    )
    region: str | None = Field(
        default=None,
        description="阿里云 region",
    )

    @classmethod
    def from_setting(
        cls,
        setting: AliyunIdentitySetting,
    ) -> AliyunIdentity:
        return cls(
            name=getattr(setting, "name"),
            type=getattr(setting, "type"),
            access_key_id=IEnviron.get_variable(
                name=getattr(setting, "osenv_access_key_id"),
                default=getattr(setting, "access_key_id"),
            ),
            access_key_secret=IEnviron.get_variable(
                name=getattr(setting, "osenv_access_key_secret"),
                default=getattr(setting, "access_key_secret"),
            ),
            region=IEnviron.get_variable(
                name=getattr(setting, "osenv_region"),
                default=getattr(setting, "region"),
            ),
            tags=getattr(setting, "tags"),
        )

    @classmethod
    def default(cls) -> AliyunIdentity:
        return cls(
            name="aliyun_default_identity",
            type=AliyunIdentityType.CHAIN,
            access_key_id=None,
            access_key_secret=None,
            region=None,
        )

    def get_client(self) -> CredentialClient:
        if self.type == AliyunIdentityType.CHAIN:
            return CredentialClient()
        elif self.type == AliyunIdentityType.AK:
            if not self.access_key_id or not self.access_key_secret:
                raise ValueError("Access key ID and Secret must be provided for AK identity")
            _config = CredentialConfig(
                type="access_key",
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
            )
            return CredentialClient(_config)
        else:
            raise ValueError(f"Unsupported Aliyun identity type: {self.type}")

    def get_credential(self) -> CredentialModel:
        _key: str = self.sha256()
        with self._credential_clients_guard:
            _client: CredentialClient | None = self._credential_clients.get(_key)
            if _client is None:
                _client = self.get_client()
                self._credential_clients[_key] = _client
        _cred: CredentialModel = _client.get_credential()
        return _cred

    def as_secret(self) -> AliyunIdentitySecret:
        _cred: CredentialModel = self.get_credential()
        return AliyunIdentitySecret(
            access_key_id=_cred.access_key_id,
            access_key_secret=_cred.access_key_secret,
            security_token=_cred.security_token or None,
        )

    def _mask_attr(
        self,
        attr_name: str,
    ) -> str | None:
        value: str | None = getattr(self, attr_name, None)
        if not value:
            return None
        if len(value) <= 4:
            return "*" * len(value)
        else:
            return "*" * (len(value) - 4) + value[-4:]

    def sha256(self) -> str:
        # describe() 掩码了密钥，不能用于指纹，否则末4位相同的不同密钥会碰撞
        _encoded: bytes = json.dumps(
            self.export(),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(_encoded).hexdigest()

    def describe(self) -> str:
        _res: dict[str, Any] = self.export()
        _res["access_key_id"] = self._mask_attr("access_key_id")
        _res["access_key_secret"] = self._mask_attr("access_key_secret")
        return json.dumps(
            _res,
            indent=4,
            ensure_ascii=False,
            sort_keys=True,
        )
