from __future__ import annotations

from typing import Protocol

from bastion.domain.bridge.base import BaseBridgeModel
from bastion.domain.run.base import BaseRunModel


class IStoreLike(Protocol):
    name: str
    
    def save_bridge(
        self,
        bridge: BaseBridgeModel,
    ) -> None: ...

    def get_bridge(
        self,
        name: str,
    ) -> BaseBridgeModel | None: ...

    def list_bridges(self) -> list[BaseBridgeModel]: ...

    def save_run(
        self,
        run: BaseRunModel,
    ) -> None: ...

    def get_run(
        self,
        run_id: str,
    ) -> BaseRunModel | None: ...

    def list_runs(
        self,
        bridge_name: str | None = None,
        limit: int | None = None,
    ) -> list[BaseRunModel]: ...
