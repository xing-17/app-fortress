from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._base import BaseAssetResource
from app.setting._vault import UnionVaultSetting


class BaseVault(
    BaseAssetResource,
    ABC,
):
    """
    Base class for asset vault resources

    Attributes:
    ----------
        uri (str):
            Asset vault URI (e.g., "scheme://bucket/key")
        frn (str):
            Asset vault FRN (Fully-Qualified Resource Name)

    Args:
    ----------
        filesystem (AssetFilesystem):
            Asset vault filesystem type
        platform (Platform):
            Asset vault operating platform
        name (str | None):
            Asset vault name
        identity (BaseIdentity | str | None):
            Asset vault identity
        description (str):
            Asset vault description information
        tags (dict[str, str]):
            Asset vault tags

    Methods:
    ----------
        from_setting(setting: UnionVaultSetting) -> BaseVault:
            Create a vault instance from a setting
        asset(rel: str, filekind: AssetFileKind | None = None, partitions: list[str] | None = None) -> BaseAsset:
            Construct an asset under this vault at the given relative path

    """

    # Enforced public class variables
    # [Inherited] filesystem: ClassVar[AssetFilesystem]
    # [Inherited] platform: ClassVar[Platform]

    # Enforced instance variables
    # [Inherited] identity: BaseIdentity | str | None
    # [Inherited] tags: dict[str, str]
    name: str | None = Field(
        default=None,
        description="[Optional] Asset vault name",
    )
    description: str = Field(
        default="",
        description="[Optional] Asset vault description information",
    )

    @classmethod
    @abstractmethod
    def from_setting(
        cls,
        setting: UnionVaultSetting,
    ) -> "BaseVault": ...

    @abstractmethod
    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> "BaseAsset": ...
