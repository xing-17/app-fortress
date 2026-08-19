from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.control.asset.base.factory import AssetFactory
from bastion.control.compute.base.factory import ComputeFactory
from bastion.domain.asset.base import BaseAssetModel
from bastion.domain.bridge.base import BaseBridgeModel
from bastion.domain.compute.base import BaseComputeModel

if TYPE_CHECKING:
    from bastion.control.compute.base.base import IComputeLike

logger = logging.getLogger(__name__)

BridgeModel = BaseBridgeModel


class Bridge(IBastionObject):
    _domain_class: type[BridgeModel] = BridgeModel

    def __init__(
        self,
        name: str,
        compute_domain: BaseComputeModel | None = None,
        asset_domains: list[BaseAssetModel] | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            compute_domain=compute_domain,
            asset_domains=asset_domains,
            description=description,
            metadata=metadata,
            tags=tags,
        )

    @property
    def compute(self) -> IComputeLike | None:
        if not self.domain.compute_domain:
            return None
        return ComputeFactory.resolve(self.domain.compute_domain)

    @property
    def assets(self) -> list[IAssetLike]:
        _result = []
        for asset_domain in self.domain.asset_domains:
            asset = AssetFactory.resolve(asset_domain)
            _result.append(asset)
        return _result

    # ----------------------------------------
    # Compute methods
    # ----------------------------------------

    def _load_compute(
        self,
        compute: IComputeLike | BaseComputeModel | dict[str, Any],
    ) -> IComputeLike:
        return ComputeFactory.resolve(compute)

    def set_compute(self, compute: IComputeLike | BaseComputeModel) -> None:
        _compute: IComputeLike = self._load_compute(compute)
        if _compute is None:
            raise ValueError("Compute can not be loaded")
        else:
            self.domain.compute_domain = _compute.domain

    def remove_compute(self) -> None:
        self.domain.compute_domain = None

    # ----------------------------------------
    # Asset methods
    # ----------------------------------------

    def _load_asset(
        self,
        asset: IAssetLike | BaseAssetModel | dict[str, Any],
    ) -> IAssetLike:
        return AssetFactory.resolve(asset)

    def _check_asset_exists(
        self,
        asset: IAssetLike | BaseAssetModel | dict[str, Any],
    ) -> bool:
        _asset: IAssetLike = self._load_asset(asset)
        if not _asset:
            raise ValueError("Asset can not be loaded")
        else:
            _seen_names = [d.name for d in self.domain.asset_domains]
            return _asset.domain.name in _seen_names

    def add_asset(self, asset: IAssetLike | BaseAssetModel | dict[str, Any]) -> None:
        _asset: IAssetLike = self._load_asset(asset)
        if not _asset:
            raise ValueError("Asset can not be loaded")
        else:
            if not self._check_asset_exists(_asset):
                self.domain.asset_domains.append(_asset.domain)
            else:
                logger.warning(f"Asset '{_asset.name}' already exists.")

    def remove_asset(self, asset: IAssetLike | BaseAssetModel) -> None:
        _asset: IAssetLike = self._load_asset(asset)
        if not _asset:
            raise ValueError("Asset can not be loaded")
        else:
            if self._check_asset_exists(_asset):
                _new_asset_domains = []
                for d in self.domain.asset_domains:
                    if d.name != _asset.domain.name:
                        _new_asset_domains.append(d)
                self.domain.asset_domains = _new_asset_domains
            else:
                logger.warning(f"Asset '{_asset.name}' does not exist.")
