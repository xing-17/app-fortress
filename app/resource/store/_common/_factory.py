from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._store import BaseStore
from app.setting._store import UnionStoreSetting


class StoreFactory:
    """
    Factory class for store instances by storesystem type.

    Attributes:
    ----------
        _registry (dict[StoreSystem, str]):
            A mapping of storesystem types to their corresponding module and class paths.

    Methods:
    ----------
        get(storesystem: StoreSystem) -> type[BaseStore]:
            Resolve and return the store class registered for the given storesystem
        load(setting: UnionStoreSetting) -> BaseStore:
            Construct a store instance from a setting using the resolved class

    Example:
    ----------
        >>> klass = StoreFactory.get(StoreSystem.FILE)
        >>> instance = klass(
        ...     name="local_store",
        ...     tags={"env": "production"},
        ... )

    """

    # Registry mapping storesystem name to corresponding store class paths.
    _registry: dict[StoreSystem, str] = {
        StoreSystem.FILE: "app.resource.store.file.store:FileStore",
        StoreSystem.OSS: "app.resource.store.oss.store:OSSStore",
    }

    @classmethod
    def get(
        cls,
        storesystem: StoreSystem,
    ) -> type[BaseStore]:
        _target: str | None = cls._registry.get(storesystem)
        if not _target:
            raise ValueError(f"No store registered for storesystem {storesystem}")

        # Dynamically import the module and callable class
        _module_path, _klass_name = _target.split(":")
        _module: ModuleType = import_module(_module_path)
        _klass: type[BaseStore] = getattr(_module, _klass_name)

        # Ensure imported class is a subclass of BaseStore
        if not isinstance(_klass, type):
            raise TypeError(f"Expecting class, got {_klass!r}.")
        if not issubclass(_klass, BaseStore):
            raise TypeError(f"Expecting subclass of BaseStore, got {_klass!r}.")
        return _klass

    @classmethod
    def load(
        cls,
        setting: UnionStoreSetting,
    ) -> BaseStore:
        _klass: type[BaseStore] = cls.get(setting.storesystem)
        if not _klass:
            raise ValueError(f"Store class for storesystem {setting.storesystem} not found")
        return _klass.from_setting(setting)
