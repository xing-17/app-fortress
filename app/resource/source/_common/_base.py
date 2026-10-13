from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from pydantic import model_validator

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.sourceprovider import SourceProvider


class BaseTaggedSourceResource(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for tagged source resources

    Args:
    ----------
        provider (SourceProvider):
            Source provider, declared as a class variable by subclasses
        tags (dict[str, str]):
            Resource tags, `provider` and `name` are always enforced into the tags

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider]

    # Enforced instance variables
    # [Inherited] tags: dict[str, str]
    def _non_override_tags(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "name": self.name,
        }


class GovernedSourceResource(
    BaseTaggedSourceResource,
    ABC,
):
    """
    Base class for source resources that must be constructed via their parent resource

    Direct construction raises ValueError unless the parent passes the sentinel
    `_authorized=True` kwarg (e.g., `BaseSource.dataset()` constructing a dataset).

    """

    @model_validator(mode="before")
    @classmethod
    def _guard_construction(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not data.pop("_authorized", False):
            raise ValueError(f"{cls.__name__} must be constructed via parent resource")
        return data
