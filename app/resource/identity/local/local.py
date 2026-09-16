from __future__ import annotations

from typing import Literal

from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity
from app.setting._identity import LocalIdentitySetting


class LocalIdentity(BaseIdentity):
    """
    Local access connection (for granularity only)

    Args:
        name (str):
            [Required] Access name (default "default")
        tags (dict[str, str]):
            [Optional] Access tags (default empty dictionary)

    Methods:
        from_setting(cls, settings: LocalIdentitySetting) -> LocalIdentity:
            从LocalIdentitySetting创建LocalIdentity实例。
        describe() -> str:
            返回Access的描述信息。

    Example:
        >>> local_identity = LocalIdentity(
        ...     name="my_local_identity",
        ...     tags={"env": "production"},
        ... )
        >>> print(local_identity.name)
        my_local_identity

    """

    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    # Inherited from BaseIdentity
    # - name: str
    # - tags: dict[str, str]

    @classmethod
    def from_setting(
        cls,
        settings: LocalIdentitySetting,
    ) -> LocalIdentity:
        return cls(
            name=getattr(settings, "name"),
            tags=getattr(settings, "tags"),
        )
