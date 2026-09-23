from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.platform import Platform
from app.setting._identity import UnionIdentitySetting


class BaseIdentity(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for identity resources

    Args:
        name (str): Identity name
        platform (Platform): Identity platform
        tags (dict[str, str]): Identity tags

    """

    name: str = Field(
        ...,
        description="[Required] Identity name",
    )
    platform: Platform = Field(
        default=Platform.LOCAL,
        description="[Required] Identity platform",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Identity tags",
    )

    @classmethod
    def from_setting(
        cls,
        setting: UnionIdentitySetting,
    ) -> BaseIdentity: ...

    @classmethod
    def default(cls) -> BaseIdentity: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    def _non_override_tags(self) -> dict[str, str]:
        return {"platform": self.platform}
