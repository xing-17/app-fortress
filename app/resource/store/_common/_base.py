from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.platform import Platform
from app.resource.identity._common import BaseIdentity
from app.setting._store import UnionStoreSetting


class BaseStore(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for store resources

    Args:
        name (str): Store name
        platform (Platform): Store platform
        identity (BaseIdentity | str | None): Asset vault identity
        tags (dict[str, str]): Store tags

    """

    name: str = Field(
        ...,
        description="[Required] Store name",
    )
    platform: Platform = Field(
        default=Platform.LOCAL,
        description="[Required] Store platform",
    )
    identity: BaseIdentity | str | None = Field(
        default=None,
        description="[Optional] Asset vault identity",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Store tags",
    )

    @classmethod
    def from_setting(
        cls,
        setting: UnionStoreSetting,
    ) -> BaseStore: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    def _non_override_tags(self):
        return {"platform": self.platform}

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res
