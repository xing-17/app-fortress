from __future__ import annotations

from typing import ClassVar

from pydantic import Field, SecretStr

from app.internal.constant.platform import Platform
from app.resource.identity._common._secret import BaseSecret


class AliyunSecret(BaseSecret):
    """
    Aliyun 密钥，由 AliyunIdentity.as_secret() 实时获取

    Attributes:
    ----------
        platform (Platform):
            平台类型，固定为Platform.ALIYUN

    Args:
    ----------
        access_key_id (str):
            阿里云 Access Key ID
        access_key_secret (SecretStr):
            阿里云 Access Key Secret
        security_token (SecretStr | None):
            STS 临时凭证的 Security Token，长期 AK 为 None

    Example:
    ----------
        >>> secret = AliyunSecret(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        >>> secret.access_key_secret.get_secret_value()
        'secretvalue'

    """

    # Enforced public class variables
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    access_key_id: str = Field(
        ...,
        description="[Required] 阿里云 Access Key ID",
    )
    access_key_secret: SecretStr = Field(
        ...,
        description="[Required] 阿里云 Access Key Secret",
    )
    security_token: SecretStr | None = Field(
        default=None,
        description="[Optional] 阿里云 STS Security Token",
    )
