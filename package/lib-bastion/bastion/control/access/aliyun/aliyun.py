from __future__ import annotations

from bastion.control.access.base.factory import AccessFactory
from bastion.control.access.base.protocol import IAccessLike
from bastion.domain.access.access import AbstractAccessDomain
from bastion.domain.access.platform import AccessPlatform
from bastion.internal.idomainobject import IDomainObject


class AliyunAccessDomain(AbstractAccessDomain):
    """
    阿里云 Access Domain class for managing Alibaba Cloud credentials.

    source: https://www.alibabacloud.com/help/zh/sdk/developer-reference/v2-manage-python-access-credentials

    Attributes:
        name: Name of the access profile.
        platform: AccessPlatform fixed to ALIYUN.
        access_key_id: 阿里云访问密钥ID。
        access_key_secret: 阿里云访问密钥Secret。
        security_token: 阿里云安全令牌，用于临时凭证。
        timeout: 请求超时时间，单位为秒。
        connect_timeout: 连接超时时间，单位为秒。
        tags: 与访问配置文件关联的标签字典。

    """

    platform: AccessPlatform = AccessPlatform.ALIYUN
    access_key_id: str | None = None
    access_key_secret: str | None = None
    security_token: str | None = None
    timeout: int | None = None
    connect_timeout: int | None = None


@AccessFactory.add(AccessPlatform.ALIYUN)
class AliyunAccess(
    IDomainObject,
    IAccessLike,
):
    """
    Aliyun access control wrapper for managing Alibaba Cloud credentials.

    Attributes:
        name: Name of the access profile.
        platform: AccessPlatform fixed to ALIYUN.
        access_key_id: 阿里云访问密钥ID。
        access_key_secret: 阿里云访问密钥Secret。
        security_token: 阿里云安全令牌，用于临时凭证。
        timeout: 请求超时时间，单位为秒。
        connect_timeout: 连接超时时间，单位为秒。
        tags: 与访问配置文件关联的标签字典。

    """

    _domain_class = AliyunAccessDomain

    def __init__(
        self,
        name: str | None = None,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        security_token: str | None = None,
        timeout: int | None = None,
        connect_timeout: int | None = None,
        tags: dict[str, str] = None,
    ):
        super().__init__(
            name=name,
            platform=AccessPlatform.ALIYUN,
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
            timeout=timeout,
            connect_timeout=connect_timeout,
            tags=tags,
        )

    def export(self) -> dict[str, str | None]:
        _key_id = self.access_key_id
        _expr_key_id = None if not _key_id else _key_id[0:4] + "******"
        _secret = self.access_key_secret
        _expr_secret = None if not _secret else _secret[0:4] + "******"
        _token = self.security_token
        _expr_token = None if not _token else _token[0:4] + "******"
        return {
            "name": self.name,
            "platform": self.platform.value,
            "access_key_id": _expr_key_id,
            "access_key_secret": _expr_secret,
            "security_token": _expr_token,
            "timeout": self.timeout,
            "connect_timeout": self.connect_timeout,
            "tags": self.tags,
        }
