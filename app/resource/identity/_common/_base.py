from __future__ import annotations

from abc import ABC

from pydantic import Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.constant.platform import Platform
from app.setting._identity import UnionIdentitySetting


class BaseIdentity(
    IAbstractDomain,
    ABC,
):
    """
    Base class for identity resources

    Args:
        name (str):
            [Required] Identity name
        platform (Platform):
            [Required] Identity platform
        tags (dict[str, str]):
            [Optional] Identity tags (default: empty dictionary)

    """

    name: str = Field(
        ...,
        description="Identity name",
    )
    platform: Platform = Field(
        default=Platform.LOCAL,
        description="Identity platform",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Identity tags",
    )

    @classmethod
    def from_setting(
        cls,
        setting: UnionIdentitySetting,
    ) -> BaseIdentity: ...

    @classmethod
    def default(cls) -> BaseIdentity: ...
