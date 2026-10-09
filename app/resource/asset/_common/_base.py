from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.identity._common._identity import BaseIdentity
from app.setting._identity import AbstractIdentitySetting


class BaseAssetResource(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Shared base class for asset resources.

    Attributes:
    ----------
        uri (str):
            Resource URI (e.g., "scheme://bucket/key")
        frn (str):
            Asset FRN (Fortress resource identifier)

    Args:
    ----------
        filesystem (AssetFilesystem):
            Asset filesystem type
        platform (Platform):
            Specifies the asset operating platform
        identity (BaseIdentity | AbstractIdentitySetting | str | None):
            Resource identity
        tags (dict[str, str]):
            Resource tags

    Methods:
    ----------
        export() -> dict[str, Any]:
            Export the resource as a dictionary

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem]
    platform: ClassVar[Platform]

    # Enforced instance variables
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(default=None)
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Resource tags",
    )

    @property
    @abstractmethod
    def uri(self) -> str: ...

    @property
    @abstractmethod
    def frn(self) -> str: ...

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "filesystem": self.filesystem,
        }

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = getattr(self.identity, "name", None)
        return _res


class GovernedAssetResource(
    BaseAssetResource,
    ABC,
):
    """
    Base class for resources that must be constructed via a parent resource,
    guarded by a sentinel `_authorized` kwarg.

    """

    @model_validator(mode="before")
    @classmethod
    def _guard_construction(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not data.pop("_authorized", False):
            raise ValueError(f"{cls.__name__} must be constructed via parent resource")
        return data
