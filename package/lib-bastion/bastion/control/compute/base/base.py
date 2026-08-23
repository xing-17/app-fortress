from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bastion.domain.compute import BaseComputeModel, ComputeKind

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.control.store.base import IStoreLike


@runtime_checkable
class IComputeAdaptorLike(Protocol):
    def load_historical_runs(
        self,
        name: str,
        **kwargs: Any,
    ) -> list[IRunLike]: ...

    def start_compute(
        self,
        name: str,
        params: dict[str, str] | None = None,
        wait: bool = True,
        **kwargs: Any,
    ) -> IRunLike: ...


@runtime_checkable
class IComputeLike(Protocol):
    domain: BaseComputeModel
    name: str
    kind: ComputeKind
    tags: dict[str, str]

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IComputeLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: BaseComputeModel,
    ) -> IComputeLike: ...

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike,
        params: dict[str, str] | None = None,
        adaptor: IComputeAdaptorLike | None = None,
    ) -> None: ...

    def cancel(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
        adaptor: IComputeAdaptorLike | None = None,
    ) -> None: ...

    def _save_run(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
    ) -> None: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...
