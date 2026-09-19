from __future__ import annotations

from abc import ABC

from pydantic import Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.constant.platform import Platform
from app.setting._store import UnionStoreSetting


class BaseStore(
    IAbstractDomain,
    ABC,
):
    """
    Base class for store resources

    Args:
        name (str):
            [Required] Store name
        platform (Platform):
            [Required] Store platform
        tags (dict[str, str]):
            [Optional] Store tags (default: empty dictionary)

    """

    name: str = Field(
        ...,
        description="Store name",
    )
    platform: Platform = Field(
        default=Platform.LOCAL,
        description="Store platform",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Store tags",
    )

    @classmethod
    def from_setting(
        cls,
        setting: UnionStoreSetting,
    ) -> BaseStore: ...
