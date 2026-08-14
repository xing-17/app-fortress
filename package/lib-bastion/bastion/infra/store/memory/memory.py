from __future__ import annotations

from bastion._internal.object import IBastionObject
from bastion.domain.bridge.base import BaseBridgeModel
from bastion.domain.run.base import BaseRunModel
from bastion.domain.store.base import BaseStoreModel, StoreKind
from bastion.infra.store.base.base import IStoreLike


class MemoryStore(
    IStoreLike,
    IBastionObject,
):
    def __init__(
        self,
        name: str,
    ) -> None:
        self.domain_model = BaseStoreModel(
            name=name,
            kind=StoreKind.MEMORY,
        )
        self._bridges: dict[str, BaseBridgeModel] = {}
        self._runs: dict[str, BaseRunModel] = {}

    def save_bridge(
        self,
        bridge: BaseBridgeModel,
    ) -> None:
        self._bridges[bridge.name] = bridge

    def get_bridge(
        self,
        name: str,
    ) -> BaseBridgeModel | None:
        return self._bridges.get(name)

    def list_bridges(self) -> list[BaseBridgeModel]:
        return list(self._bridges.values())

    def save_run(
        self,
        run: BaseRunModel,
    ) -> None:
        self._runs[run.id] = run

    def get_run(
        self,
        run_id: str,
    ) -> BaseRunModel | None:
        return self._runs.get(run_id)

    def list_runs(
        self,
        bridge_name: str | None = None,
        limit: int | None = None,
    ) -> list[BaseRunModel]:
        result = []
        for run in self._runs.values():
            if bridge_name is None or run.bridge_name == bridge_name:
                result.append(run)
        result.sort(key=lambda r: r.created_at, reverse=True)
        return result if limit is None else result[:limit]

    def export(self) -> dict[str, str]:
        return {
            "name": self.domain_model.name,
            "kind": self.domain_model.kind,
            "n_bridge_count": len(self._bridges),
            "n_run_count": len(self._runs),
        }
