from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.resource.identity._common._identitysecret import BaseIdentitySecret
from app.setting._identity import UnionIdentitySetting


class BaseIdentity(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for identity resources

    Args:
    ----------
        name (str): Identity name
        tags (dict[str, str]): Identity tags

    Methods:
    ----------
        as_secret() -> BaseIdentitySecret:
            Produce a fresh secret on every call, it may reach the network and must not be cached.

    """

    # Enforced public class variables
    platform: ClassVar[Platform]

    # Enforced instance variables
    name: str = Field(
        ...,
        description="[Required] Identity name",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Identity tags",
    )

    @classmethod
    @abstractmethod
    def from_setting(
        cls,
        setting: UnionIdentitySetting,
    ) -> BaseIdentity: ...

    @classmethod
    @abstractmethod
    def default(cls) -> BaseIdentity: ...

    @abstractmethod
    def as_secret(self) -> BaseIdentitySecret: ...

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "identity",
                f"platform={self.platform}",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        return {"platform": self.platform}
