from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.computeruntime import ComputeRuntime
from app.resource.compute._common._compute import BaseCompute
from app.setting._compute import UnionComputeSetting


class ComputeFactory:
    """
    Factory class for compute instances by runtime type.

    Attributes:
    ----------
        _registry (dict[ComputeRuntime, str]):
            A mapping of runtime types to their corresponding module and class paths.

    Methods:
    ----------
        get(runtime: ComputeRuntime | str) -> type[BaseCompute]:
            Resolve and return the compute class registered for the given runtime
        load(setting: UnionComputeSetting) -> BaseCompute:
            Construct a compute instance from a setting using the resolved class

    Example:
    ----------
        >>> klass = ComputeFactory.get(ComputeRuntime.PYENTRYPOINT)
        >>> instance = klass(
        ...     name="local_fetch",
        ...     entrypoint="app.entrypoint:run_dataset",
        ... )

    """

    # Registry mapping runtime types to their corresponding module and class paths.
    _registry: dict[ComputeRuntime, str] = {
        ComputeRuntime.PYENTRYPOINT: "app.resource.compute.pyentrypoint.compute:PyEntrypointCompute",
        ComputeRuntime.FC: "app.resource.compute.fc.compute:FCCompute",
    }

    @classmethod
    def get(
        cls,
        runtime: ComputeRuntime | str,
    ) -> type[BaseCompute]:
        _target: str | None = cls._registry.get(runtime)
        if not _target:
            raise ValueError(f"No compute registered for runtime {runtime}")

        # Dynamically import the module and callable class
        _module_path, _klass_name = _target.split(":")
        _module: ModuleType = import_module(_module_path)
        _klass: type[BaseCompute] = getattr(_module, _klass_name)

        # Ensure imported class is a subclass of BaseCompute
        if not isinstance(_klass, type):
            raise TypeError(f"Expecting class, got {_klass!r}.")
        if not issubclass(_klass, BaseCompute):
            raise TypeError(f"Expecting subclass of BaseCompute, got {_klass!r}.")
        return _klass

    @classmethod
    def load(
        cls,
        setting: UnionComputeSetting,
    ) -> BaseCompute:
        _klass: type[BaseCompute] = cls.get(setting.runtime)
        return _klass.from_setting(setting)
