from __future__ import annotations

import logging
from typing import Any

from bastion._internal.object import IBastionObject
from bastion.control.bridge.bridge import Bridge, BridgeModel
from bastion.control.run.run import Run, RunModel
from bastion.control.store.base.base import IStoreLike
from bastion.domain.store.base import BaseStoreModel, StoreKind

logger = logging.getLogger(__name__)


class MemoryStoreModel(BaseStoreModel):
    kind: StoreKind = StoreKind.MEMORY


class MemoryStore(
    IBastionObject,
    IStoreLike,
):
    _domain_class = MemoryStoreModel

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__(
            name=name,
        )
        self._bridges: dict[str, BridgeModel] = {}
        self._runs: dict[str, RunModel] = {}

    # ------------------------------------------------------------------
    # Bridge
    # ------------------------------------------------------------------

    def check_bridge_exists(
        self,
        name: str,
    ) -> bool:
        return name in self._bridges

    def save_bridge(
        self,
        bridge: Bridge | BridgeModel,
    ) -> None:
        if isinstance(bridge, Bridge):
            bridge: BridgeModel = bridge.domain
        self._bridges[bridge.name] = bridge

    def get_bridge(
        self,
        name: str,
    ) -> Bridge | None:
        _model: BridgeModel | None = self._bridges.get(name)
        if _model is None:
            return None
        return Bridge.from_domain(_model)

    def list_bridges(
        self,
        limit: int | None = None,
    ) -> list[Bridge]:
        _all_bridge_models: list[BridgeModel] = list(self._bridges.values())
        _result: list[Bridge] = []
        for m in _all_bridge_models:
            _result.append(Bridge.from_domain(m))
        return self._slice_from_list(_result, limit)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def check_run_exists(
        self,
        run_id: str,
    ) -> bool:
        return run_id in self._runs

    def save_run(
        self,
        run: Run | RunModel,
    ) -> None:
        if isinstance(run, Run):
            run: RunModel = run.domain
        self._runs[run.id] = run

    def get_run(
        self,
        run_id: str,
    ) -> Run | None:
        _model: RunModel | None = self._runs.get(run_id)
        if _model is None:
            return None
        return Run.from_domain(_model)

    def list_runs(
        self,
        bridge_name: str | None = None,
        limit: int | None = None,
    ) -> list[Run]:
        _all_runs: list[Run] = []
        for run in self._runs.values():
            if bridge_name is None or run.bridge_name == bridge_name:
                _all_runs.append(Run.from_domain(run))
        _all_runs.sort(key=lambda r: r.created_at, reverse=True)
        return self._slice_from_list(_all_runs, limit)

    def _get_counts(self) -> dict[str, int]:
        return {
            "bridges": len(self._bridges),
            "runs": len(self._runs),
        }

    def export(self) -> dict[str, Any]:
        _super_export: dict[str, Any] = super().export()
        _counts: dict[str, int] = self._get_counts()
        _super_export["counts"] = _counts
        return _super_export
