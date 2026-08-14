from __future__ import annotations

from typing import Any, Callable

from bastion._internal.object import IBastionObject
from bastion.control.run.run import IRunLike
from bastion.domain.compute.base import BaseComputeModel, ComputeKind
from bastion.infra.store.base.base import IStoreLike


class LocalPyFnComputeModel(BaseComputeModel):
    kind: ComputeKind = ComputeKind.LOCAL_PY_FN


class LocalPyFnCompute(IBastionObject):
    def __init__(
        self,
        name: str,
        fn: Callable[..., Any],
        tags: dict[str, str] | None = None,
    ):
        super().__init__()
        self.domain: LocalPyFnComputeModel = LocalPyFnComputeModel(
            name=name,
            kind=ComputeKind.LOCAL_PY_FN,
            tags=tags or {},
        )
        self.fn: Callable[..., Any] = fn

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike,
        params: dict[str, str] | None = None,
    ) -> Any:
        if params is None:
            params = {}
        try:
            run.start()
            if store is not None:
                store.save_run(run.domain)
            self.fn(**params)
            run.succeed()
            if store is not None:
                store.save_run(run.domain)
        except Exception:
            run.fail()
            if store is not None:
                store.save_run(run.domain)
            raise
