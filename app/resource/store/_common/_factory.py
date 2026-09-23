from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.platform import Platform
from app.resource.store._common._base import BaseStore
from app.setting._store import UnionStoreSetting


class StoreFactory:
    """
    Factory class for store instances by platform type.

    Attributes:
        _registry (dict[Platform, str]):
            a mapping of platform names to their corresponding store class paths.

    Example:
        >>> klass = StoreFactory.get(Platform.LOCAL)
        >>> instance = klass(
        ...     name="local_store",
        ...     tags={"env": "production"},
        ... )

    """

    # Registry mapping platform name to corresponding store class paths.
    _registry: dict[Platform, str] = {
        Platform.LOCAL: "app.resource.store.local.duckdb:DuckDbStore",
        Platform.ALIYUN: "app.resource.store.aliyun.ots:OtsStore",
    }

    @classmethod
    def get(
        cls,
        platform: Platform,
    ) -> type[BaseStore]:
        _target: str | None = cls._registry.get(platform)
        if not _target:
            raise ValueError(f"No store registered for platform {platform}")

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
        _klass: type[BaseStore] = cls.get(setting.platform)
        if not _klass:
            raise ValueError(f"Store class for platform {setting.platform} not found")
        return _klass.from_setting(setting)
