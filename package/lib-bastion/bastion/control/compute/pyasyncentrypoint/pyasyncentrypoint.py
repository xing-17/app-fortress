from __future__ import annotations

import importlib
import signal
from datetime import datetime
from multiprocessing import Process, Queue
from typing import TYPE_CHECKING, Any, Self

from bastion._internal.object import IBastionObject
from bastion.control.compute.base.base import IComputeLike
from bastion.control.compute.base.factory import ComputeFactory
from bastion.domain.compute import BaseComputeModel, ComputeKind

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.control.store.base.base import IStoreLike


class PyAsyncEntrypointModel(BaseComputeModel):
    kind: ComputeKind = ComputeKind.PY_ASYNC_ENTRYPOINT
    entrypoint: str


def run_in_async(
    entrypoint: str,
    params: dict[str, str],
    queue: Queue,
) -> None:
    try:
        module_path, func_name = entrypoint.rsplit(".", 1)
        module = importlib.import_module(module_path)
        getattr(module, func_name)(**params)
        queue.put((True, None))
    except Exception as exc:
        queue.put((False, exc))


@ComputeFactory.register(ComputeKind.PY_ASYNC_ENTRYPOINT.value)
class PyAsyncEntrypointCompute(
    IBastionObject,
    IComputeLike,
):
    _domain_class: type[PyAsyncEntrypointModel] = PyAsyncEntrypointModel

    @classmethod
    def from_domain(
        cls,
        domain: PyAsyncEntrypointModel,
    ) -> Self:
        obj = super().from_domain(domain)
        obj._process = None
        obj._queue = None
        return obj

    def __init__(
        self,
        name: str,
        entrypoint: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            entrypoint=entrypoint,
            tags=tags,
        )
        self._process: Process | None = None
        self._queue: Queue | None = None

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

        self._queue = self._queue or Queue()
        self._process = self._process or Process(
            target=run_in_async,
            args=(self.domain.entrypoint, params, self._queue),
            daemon=True,
        )

        run.start()
        self._save_run(run, store)

        try:
            self._process.start()
            self._process.join()  # Wait for the process to finish

            exitcode = self._process.exitcode
            if exitcode == 0:
                success, exc = self._queue.get_nowait()
                if success:
                    run.succeed()
                else:
                    run.fail()
                    raise exc
            elif exitcode == -signal.SIGTERM:
                run.cancel()
            else:
                run.fail()
        finally:
            self._save_run(run, store)
            self._process = None
            self._queue = None

    def cancel(
        self,
        **kwargs: Any,
    ) -> None:
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join()

    def _save_run(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
    ) -> None:
        if store is not None:
            store.save_run(run)
