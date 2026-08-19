from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bastion.domain.store.base import BaseStoreModel

if TYPE_CHECKING:
    from bastion.control.bridge.bridge import Bridge
    from bastion.control.run.run import Run


@runtime_checkable
class IStoreLike(Protocol):
    # IBastionObject attributes
    domain: BaseStoreModel

    # store attributes
    name: str
    kind: str

    # additional attributes for integrity
    logic_name: str | None
    sha256: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IStoreLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: BaseStoreModel,
    ) -> IStoreLike: ...

    # ------------------------------------------------
    # Bridge related methods
    # ------------------------------------------------
    def check_bridge_exists(
        self,
        name: str,
    ) -> bool: ...

    def save_bridge(
        self,
        bridge: Bridge,
    ) -> None: ...

    def get_bridge(
        self,
        name: str,
    ) -> Bridge | None: ...

    def list_bridges(
        self,
        limit: int | None = None,
    ) -> list[Bridge]: ...

    def delete_bridge(
        self,
        name: str,
    ) -> None: ...

    # ------------------------------------------------
    # Run related methods
    # ------------------------------------------------
    def check_run_exists(
        self,
        run_id: str,
    ) -> bool: ...

    def save_run(
        self,
        run: Run,
    ) -> None: ...

    def get_run(
        self,
        run_id: str,
    ) -> Run | None: ...

    def list_runs(
        self,
        bridge_name: str | None = None,
        limit: int | None = None,
    ) -> list[Run]: ...

    def delete_run(
        self,
        run_id: str,
    ) -> None: ...

    def delete_runs(
        self,
        bridge_name: str,
    ) -> None: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...
