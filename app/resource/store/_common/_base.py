from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import Field

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
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
    storesystem: StoreSystem = Field(
        ...,
        description="[Required] Store system",
    )
    platform: Platform = Field(
        ...,
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
    def frn(self) -> str:
        return f"store:platform={self.platform}:storesystem={self.storesystem}:name={self.name}"

    def _non_override_tags(self):
        return {
            "storesystem": self.storesystem,
            "platform": self.platform,
            "name": self.name,
        }

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res
