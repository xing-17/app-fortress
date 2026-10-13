from __future__ import annotations

from importlib import import_module
from types import ModuleType

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source._common._source import BaseSource
from app.setting._source import UnionSourceSetting


class SourceFactory:
    """
    Factory class for source instances by provider type.

    Attributes:
    ----------
        _registry (dict[SourceProvider, str]):
            A mapping of source providers to their corresponding module and class paths.

    Methods:
    ----------
        get(provider: SourceProvider | str) -> type[BaseSource]:
            Resolve and return the source class registered for the given provider
        load(setting: UnionSourceSetting) -> BaseSource:
            Construct a source instance from a setting using the resolved class

    Example:
    ----------
        >>> klass = SourceFactory.get(SourceProvider.TUSHARE)
        >>> instance = klass(
        ...     name="prod_tushare",
        ...     key="token",
        ...     vault="my_vault",
        ...     store="my_store",
        ... )

    """

    # Registry mapping provider to corresponding source class paths.
    _registry: dict[SourceProvider, str] = {
        SourceProvider.TUSHARE: "app.resource.source.tushare.source:TushareSource",
    }

    @classmethod
    def get(
        cls,
        provider: SourceProvider | str,
    ) -> type[BaseSource]:
        _target: str | None = cls._registry.get(provider)
        if not _target:
            raise ValueError(f"No source registered for provider '{provider}'")

        # Dynamically import the module and callable class
        _module_path, _klass_name = _target.split(":")
        _module: ModuleType = import_module(_module_path)
        _klass: type[BaseSource] = getattr(_module, _klass_name)

        # Ensure imported class is a subclass of BaseSource
        if not isinstance(_klass, type):
            raise TypeError(f"Expecting class, got {_klass!r}.")
        if not issubclass(_klass, BaseSource):
            raise TypeError(f"Expecting subclass of BaseSource, got {_klass!r}.")
        return _klass

    @classmethod
    def load(
        cls,
        setting: UnionSourceSetting,
    ) -> BaseSource:
        _klass: type[BaseSource] = cls.get(setting.provider)
        return _klass.from_setting(setting)
