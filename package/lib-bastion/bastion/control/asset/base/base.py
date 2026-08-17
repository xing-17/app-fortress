from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel


@runtime_checkable
class IAssetLike(Protocol):
    domain: BaseAssetModel
    name: str
    kind: AssetKind
    platform: AssetPlatform
    description: str | None
    owner: str | None
    metadata: dict[str, Any]
    tags: dict[str, str]
    sha256: str
    logic_name: str | None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IAssetLike: ...
    
    @classmethod
    def from_domain(
        cls,
        domain: BaseAssetModel,
    ) -> IAssetLike: ...

    def get_location_uri(self) -> str: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> dict[str, Any]: ...
