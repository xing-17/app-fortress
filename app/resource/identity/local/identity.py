from __future__ import annotations

from typing import ClassVar

from app.internal.constant.platform import Platform
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.local.identitysecret import LocalIdentitySecret
from app.setting._identity import LocalIdentitySetting


class LocalIdentity(BaseIdentity):
    """
    Local access connection (for granularity only)

    Attributes:
    ----------
        platform (Platform):
            Platform type, fixed as Platform.LOCAL

    Args:
    ----------
        name (str): Access name
        tags (dict[str, str]): Access tags

    Methods:
    ----------
        from_setting(cls, settings: LocalIdentitySetting) -> LocalIdentity:
            creates a LocalIdentity instance from a LocalIdentitySetting object.
        as_secret() -> LocalIdentitySecret:
            returns an empty secret, local access needs none.
        describe() -> str:
            returns the description of the Access.

    Example:
    ----------
        >>> local_identity = LocalIdentity(
        ...     name="my_local_identity",
        ...     tags={"env": "production"},
        ... )
        >>> print(local_identity.name)
        my_local_identity

    """

    # Enforced public class variables
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]

    @classmethod
    def from_setting(
        cls,
        setting: LocalIdentitySetting,
    ) -> LocalIdentity:
        return cls(
            name=getattr(setting, "name"),
            tags=getattr(setting, "tags"),
        )

    @classmethod
    def default(cls) -> LocalIdentity:
        return cls(name="local_default_identity")

    def as_secret(self) -> LocalIdentitySecret:
        return LocalIdentitySecret()
