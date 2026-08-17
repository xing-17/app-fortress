from __future__ import annotations

import importlib
from typing import Any, Callable

from bastion._internal.object import IBastionObject
from bastion.control.compute.base.base import IComputeLike
from bastion.control.run import IRunLike
from bastion.control.store.base.base import IStoreLike
from bastion.domain.compute.base import BaseComputeModel, ComputeKind


class PyEntrypointModel(BaseComputeModel):
    """
    Compute model for Python function entrypoint execution.

    Attributes:
        kind (ComputeKind): Fixed as PY_ENTRYPOINT for Python function execution.
        entrypoint (str): Fully qualified path to the Python function (e.g., "module.submodule.function").
        name (str): Name of the compute resource (inherited).
        tags (dict[str, str]): Tags associated with the compute resource (inherited).

    Methods:
        from_any(value): Convert dict or instance to compute model (inherited).
        export(): Export the compute model as a dictionary (inherited).
        describe(): Export compute as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        model = PyEntrypointModel(
            name="data_processor",
            entrypoint="myapp.tasks.process_data"
        )
        exported = model.export()
        ```

    """

    kind: ComputeKind = ComputeKind.PY_ENTRYPOINT
    entrypoint: str


class PyEntrypointCompute(
    IBastionObject,
    IComputeLike,
):
    """
    Compute resource for executing Python functions as entrypoints.

    This class provides the control layer for managing and executing Python functions
    as compute resources, handling run lifecycle, and storing execution results.

    Attributes:
        domain (PyEntrypointModel): Domain model containing compute configuration.
        name (str): Name of the compute resource.
        entrypoint (str): Fully qualified path to the Python function.
        tags (dict[str, str]): Tags associated with the compute resource.

    Methods:
        get_entrypoint(): Retrieve the resolved Python callable function.
        execute(run, store, params): Execute the entrypoint function with run management.

    Example:
        ```python
        from bastion.control.compute.pyentrypoint import PyEntrypointCompute
        from bastion.control.run import Run

        # Create compute resource
        compute = PyEntrypointCompute(
            name="my_task",
            entrypoint="myapp.tasks.process_data",
            tags={"env": "production", "version": "1.0"}
        )

        # Get the callable
        func = compute.get_entrypoint()

        # Execute with run management
        run = Run(name="task_run_001")
        result = compute.execute(
            run=run,
            store=my_store,
            params={"input_file": "data.csv", "output_dir": "/tmp"}
        )
        ```

    """

    _domain_class: type[PyEntrypointModel] = PyEntrypointModel

    def __init__(
        self,
        name: str,
        entrypoint: str,
        tags: dict[str, str] | None = None,
    ):
        super().__init__(
            name=name,
            entrypoint=entrypoint,
            tags=tags or {},
        )

    def get_entrypoint(self) -> Callable[..., Any]:
        return self._resolve_entrypoint()

    def _resolve_entrypoint(self) -> Callable[..., Any]:
        module_path, func_name = self.domain.entrypoint.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        if params is None:
            params = {}

        # Start the run and fail early if cant save
        run.start()
        self._save_run(run, store)

        # Execute the entrypoint function
        try:
            ep: Callable[..., Any] = self.get_entrypoint()
            ep(**params)
            run.succeed()
        except Exception:
            run.fail()
            raise
        finally:
            self._save_run(run, store)
