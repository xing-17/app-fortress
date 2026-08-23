from __future__ import annotations

import importlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from bastion._internal.object import IBastionObject
from bastion.control.compute.base.base import IComputeLike
from bastion.control.compute.base.factory import ComputeFactory
from bastion.domain.compute import BaseComputeModel, ComputeKind

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.control.store.base.base import IStoreLike


class PyEntrypointModel(BaseComputeModel):
    kind: ComputeKind = ComputeKind.PY_ENTRYPOINT
    entrypoint: str


@ComputeFactory.register(ComputeKind.PY_ENTRYPOINT.value)
class PyEntrypointCompute(
    IBastionObject,
    IComputeLike,
):
    _domain_class: type[PyEntrypointModel] = PyEntrypointModel

    def _resolve_entrypoint(self) -> Callable[..., Any]:
        module_path, func_name = self.domain.entrypoint.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    def inspect(
        self,
        store: IStoreLike | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[IRunLike]:
        if store is not None:
            return store.list_runs(
                compute_name=self.domain.name, since=since, until=until, limit=limit
            )
        return []

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
        params: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        if params is None:
            params = {}

        # Start the run and fail early if cant save
        run.start()
        self._save_run(run, store)

        # Execute the entrypoint function
        try:
            ep: Callable[..., Any] = self._resolve_entrypoint()
            ep(**params)
            run.succeed()
        except Exception:
            run.fail()
            raise
        finally:
            self._save_run(run, store)

    def cancel(
        self,
        **kwargs: Any,
    ) -> None:
        pass  # No-op for Python entrypoint compute, as cancellation is not supported

    def _save_run(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
    ) -> None:
        if store is not None:
            store.save_run(run)
