from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bastion.control.asset.base.base import IAssetLike
from bastion.control.bridge.bridge import Bridge
from bastion.control.run.run import Run
from bastion.control.store.base.base import IStoreLike

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Hub:
    def __init__(
        self,
        store: IStoreLike,
    ) -> None:
        self._store = store
        self._cache_bridges: dict[str, Bridge] = {}
        self._cache_runs: dict[str, Run] = {}        

    @property
    def store(self) -> IStoreLike:
        return self._store
    
    def list_bridges(self) -> list[Bridge]:
        return self._store.list_bridges()
    
    def list_runs(self) -> list[Run]:
        return self._store.list_runs()
    
    def load(self) -> None:
        _all_bridges = self.list_bridges()
        _all_runs = self.list_runs()
        self._cache_bridges = {bridge.name: bridge for bridge in _all_bridges}
        self._cache_runs = {run.id: run for run in _all_runs}
    
    def list_assets(self) -> list[IAssetLike]:
        _all_assets: list[IAssetLike] = []
        _seen_assets: set[str] = set()
        if not self._cache_bridges:
            self.load()
        for bridge in self._cache_bridges.values():
            for asset in bridge.assets:
                if asset.name not in _seen_assets:
                    _all_assets.append(asset)
                    _seen_assets.add(asset.name)
        return _all_assets
    
    def list_computes(self) -> list[str]:
        _all_computes: set[str] = set()
        if not self._cache_bridges:
            self.load()
        for bridge in self._cache_bridges.values():
            if bridge.compute is not None:
                _all_computes.add(bridge.compute.name)
        return list(_all_computes)

    def register(
        self,
        bridge: Bridge | IAssetLike,
    ) -> None:
        if isinstance(bridge, IAssetLike):
            # sugar: register(asset) → Bridge(name=asset.name, assets=[asset])
            bridge = Bridge(
                name=bridge.name,
                asset_domains=[bridge.domain],
            )
            self._store.save_bridge(bridge)
            logger.debug(f"Registered bridge OK: '{bridge.name}' (from asset).")
        elif isinstance(bridge, Bridge):
            self._store.save_bridge(bridge)
            logger.debug(f"Registered bridge OK: '{bridge.name}'.")
        else:
            _cls_name = type(bridge).__name__
            raise TypeError(f"Expected Bridge or IAssetLike, got {_cls_name}.")
        
        self.load()  # Refresh cache after registering

    def unregister(
        self,
        bridge_name: str,
    ) -> None:
        is_exists = self._store.check_bridge_exists(bridge_name)
        if not is_exists:
            logger.warning(f"Bridge '{bridge_name}' not found in store.")
            return
        else:
            self._store.delete_bridge(bridge_name)
            self._store.delete_runs(bridge_name)
            logger.info(f"Unregistered bridge OK: '{bridge_name}'.")
            
        self.load()  # Refresh cache after unregistering

    def run(
        self,
        bridge_name: str,
        params: dict[str, Any] | None = None,
    ) -> Run:
        # Get bridge from store, raise error if not found
        bridge: Bridge | None = self._store.get_bridge(bridge_name)
        if bridge is None:
            raise ValueError(f"Bridge '{bridge_name}' not found.")

        # Get compute from bridge, raise error if not configured
        compute = bridge.compute
        if compute is None:
            raise ValueError(f"Bridge '{bridge_name}' has no compute configured.")

        run = Run(bridge_name=bridge_name)
        compute.execute(run=run, store=self._store, params=params)
        self.load()  # Refresh cache after running
        return run
