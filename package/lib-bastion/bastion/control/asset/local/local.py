from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel


class LocalAssetModel(BaseAssetModel):
    path: str = Field(
        ...,
        description="Path of the local asset",
    )

    def export(self) -> dict[str, Any]:
        return {
            **super().export(),
            "path": self.path,
        }


class LocalAsset(IBastionObject):
    def __init__(
        self,
        name: str,
        kind: AssetKind,
        path: str,
        description: str | None = None,
        owner: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ):
        super().__init__()
        self.domain: LocalAssetModel = LocalAssetModel(
            name=name,
            kind=AssetKind.from_any(kind),
            path=path,
            platform=AssetPlatform.LOCAL,
            description=description,
            owner=owner,
            metadata=metadata or {},
            tags=tags or {},
        )

    def _resolve_path(self) -> Path:
        return Path(self.domain.path).expanduser().resolve()

    def get_location_uri(self) -> str:
        _resolved_path = self._resolve_path()
        return str(_resolved_path)

    def export(self) -> dict[str, Any]:
        return {
            "name": self.domain.name,
            "domain": self.domain.export(),
        }
