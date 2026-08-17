from __future__ import annotations

from typing import Any, Protocol

from bastion.control.run import IRunLike
from bastion.domain.compute.base import BaseComputeModel, ComputeKind
from bastion.infra.store.base.base import IStoreLike

ComputeModel = BaseComputeModel


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
        domain: ComputeModel,
    ) -> IComputeLike: ...

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike,
        params: dict[str, str] | None = None,
    ) -> None: ...

    def _save_run(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
    ) -> None:
        if store is not None:
            store.save_run(run.domain)

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...
