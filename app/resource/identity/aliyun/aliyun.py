from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.internal.util.environ import IEnviron
from app.resource.identity._common._base import BaseIdentity
from app.setting._identity import AliyunIdentitySetting


class AliyunIdentity(BaseIdentity):
    """
    Aliyun Identity Connection

    Args:
        name (str):
            [Required] Access名称(默认"default")
        type (AliyunIdentityType):
            [Optional] Identity类型(默认CHAIN)
        access_key_id (str | None):
            [Optional] 阿里云Access Key ID(默认None)
        access_key_secret (str | None):
            [Optional] 阿里云Access Key Secret(默认None)
        tags (dict[str, str]):
            [Optional] Access标签(默认空字典)

    Methods:
        from_setting(cls, settings: AliyunIdentitySetting) -> AliyunIdentity:
            从AliyunIdentitySetting创建AliyunIdentity实例。
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

    # Inherited from BaseIdentity
    # - name: str
    # - tags: dict[str, str]
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    type: AliyunIdentityType = Field(
        default=AliyunIdentityType.CHAIN,
        description="Aliyun identity type",
    )
    access_key_id: str | None = Field(
        default=None,
        description="Aliyun access key ID",
    )
    access_key_secret: str | None = Field(
        default=None,
        description="Aliyun access key secret",
    )

    @classmethod
    def from_setting(
        cls,
        settings: AliyunIdentitySetting,
    ) -> AliyunIdentity:
        return cls(
            name=getattr(settings, "name"),
            type=getattr(settings, "type"),
            access_key_id=IEnviron.get_variable(
                name=getattr(settings, "osenv_access_key_id"),
                default=getattr(settings, "access_key_id"),
            ),
            access_key_secret=IEnviron.get_variable(
                name=getattr(settings, "osenv_access_key_secret"),
                default=getattr(settings, "access_key_secret"),
            ),
            tags=getattr(settings, "tags"),
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
