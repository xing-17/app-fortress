from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset.base import BaseAssetModel

logger = logging.getLogger(__name__)


class LocalAssetModel(BaseAssetModel):
    path: str = Field(
        ...,
        description="Path of the local asset",
    )


class LocalAsset(
    IBastionObject,
    IAssetLike,
):
    _domain_class: type[LocalAssetModel] = LocalAssetModel

    def _resolve_path(self) -> Path:
        return Path(self.path).expanduser().resolve()

    def get_location_uri(self) -> str:
        return str(self._resolve_path())
