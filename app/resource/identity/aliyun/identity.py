from __future__ import annotations

import json
from typing import Any, Literal

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.client import CredentialModel
from alibabacloud_credentials.models import Config as CredentialConfig
from pydantic import Field

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.internal.util.environ import IEnviron
from app.resource.identity._common._identity import BaseIdentity
from app.setting._identity import AliyunIdentitySetting


class AliyunIdentity(BaseIdentity):
    """
    Aliyun Identity 身份认证

        ref: https://help.aliyun.com/en/sdk/developer-reference/v2-manage-python-access-credentials

    Args:
        name (str): Access名称
        type (AliyunIdentityType): Identity类型(默认'chain')
        access_key_id (str | None): 阿里云Access Key ID(默认None)
        access_key_secret (str | None): 阿里云Access Key Secret(默认None)
        region (str | None): Aliyun region(默认None)
        tags (dict[str, str]): Access标签(默认空字典)

    Methods:
        from_setting(cls, settings: AliyunIdentitySetting) -> AliyunIdentity:
            从AliyunIdentitySetting创建AliyunIdentity实例。
        get_credential() -> CredentialModel:
            获取Aliyun身份的凭证信息。
        describe() -> str:
            返回Access的描述信息，敏感信息会被掩码。

    Example:
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

    # 继承自 BaseIdentity
    # - name: str
    # - tags: dict[str, str]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
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
        _client: CredentialClient = self.get_client()
        _cred: CredentialModel = _client.get_credential()
        return _cred

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
