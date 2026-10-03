from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.identity._common._identity import BaseIdentity
from app.setting._identity import AbstractIdentitySetting


class BaseStoreResource(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Shared field/behavior mixin for the store/database/table hierarchy.

    Args:
        name (str): Resource name
        storesystem (StoreSystem): Store system
        platform (Platform): Store platform
        identity (BaseIdentity | AbstractIdentitySetting | str | None): Resource identity
        tags (dict[str, str]): Resource tags

    """

    name: str = Field(...)
    storesystem: StoreSystem = Field(...)
    platform: Platform = Field(...)
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(default=None)
    tags: dict[str, str] = Field(default_factory=dict)

    def _handle_io_error(
        self,
        exception: Exception,
        strict: bool = False,
    ) -> None:
        if strict:
            raise exception

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "storesystem": self.storesystem,
            "platform": self.platform,
            "name": self.name,
        }

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res


class GovernedStoreResource(BaseStoreResource, ABC):
    """
    Base class for resources that must be constructed via a parent resource's factory
    method (BaseDatabase/BaseTable), guarded by a sentinel `_authorized` kwarg plus a
    single-path-segment `name` check (no `/`, `\\`, `.` or `..`).
    """

    @model_validator(mode="before")
    @classmethod
    def _guard_construction(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not data.pop("_authorized", False):
            raise ValueError(f"{cls.__name__} must be constructed via parent resource")
        return data

    @model_validator(mode="after")
    def _validate_name(self) -> "GovernedStoreResource":
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} name must not be empty")
        if self.name in (".", ".."):
            raise ValueError(f"{self.__class__.__name__} name must not be '.' or '..'")
        if "/" in self.name or "\\" in self.name:
            raise ValueError(f"{self.__class__.__name__} name must not contain path separators")
        return self
