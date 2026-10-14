from __future__ import annotations

import threading

from app.internal.constant.sourceprovider import SourceProvider
from app.resource._global.setting import GlobalSetting
from app.resource.source._common._factory import SourceFactory
from app.resource.source._common._source import BaseSource
from app.setting._source import AbstractSourceSetting, UnionSourceSetting
from app.setting.system import SystemSetting


class GlobalSources:
    """
    Global Source resource manager.

    Attributes:
    ----------
        sources (dict[str, BaseSource] | None):
            Global Source dict, keyed by Source name, valued by Source instance
        _lock (threading.RLock):
            Thread lock, used to ensure thread safety

    Methods:
    ----------
        load() -> None:
            Load global Sources from the system setting
        get_source(name: str, strict: bool = True) -> BaseSource | None:
            Get the Source with the given name; raises if missing and strict is True
        resolve(value: BaseSource | UnionSourceSetting | str | None, default: BaseSource | None = None, provider: SourceProvider | None = None) -> BaseSource:
            Resolve the given instance/setting/name/None into a concrete Source instance, without registering it into the global dict
        list_source_names(provider: SourceProvider | None = None) -> list[str]:
            List all Source names
        list_sources(provider: SourceProvider | None = None) -> list[BaseSource]:
            List all Source instances
        reset() -> None:
            Reset the global Source manager

    Example:
    ----------
        >>> from app.resource._global.sources import GlobalSources
        >>> source = GlobalSources.get_source("my_source")

    """

    sources: dict[str, BaseSource] | None = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls) -> None:
        _sources: dict[str, BaseSource] = {}
        _sys_setting: SystemSetting = GlobalSetting.get_system()
        _source_settings: list[UnionSourceSetting] = _sys_setting.sources
        for _source_setting in _source_settings:
            _name: str = _source_setting.name
            if _name in _sources:
                raise ValueError(f"Duplicate source entry '{_name}'")
            try:
                _sources[_name] = SourceFactory.load(_source_setting)
            except Exception as e:
                raise ValueError(f"Failed to load source '{_name}': {e}") from e
        with cls._lock:
            cls.sources = _sources

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.sources is not None:
            return
        with cls._lock:
            if cls.sources is None:
                cls.load()

    @classmethod
    def get_source(
        cls,
        name: str,
        strict: bool = True,
    ) -> BaseSource | None:
        with cls._lock:
            cls._ensure_loaded()
            if strict and name not in cls.sources:
                raise ValueError(f"Source '{name}' not found")
            return cls.sources.get(name)

    @classmethod
    def resolve(
        cls,
        value: BaseSource | UnionSourceSetting | str | None,
        default: BaseSource | None = None,
        provider: SourceProvider | None = None,
    ) -> BaseSource:
        if isinstance(value, BaseSource):
            _res: BaseSource = value
        elif value is None:
            if default is None:
                raise ValueError("Value is None and no default provided")
            if not isinstance(default, BaseSource):
                raise ValueError(f"Default must be type 'BaseSource', got {type(default)}")
            _res: BaseSource = default
        elif isinstance(value, str):
            _res: BaseSource = cls.get_source(value, strict=True)
        elif isinstance(value, AbstractSourceSetting):
            _res: BaseSource = SourceFactory.load(value)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        if provider and _res.provider != provider:
            raise ValueError(f"Source '{_res.name}' does not match provider '{provider}'")

        return _res

    @classmethod
    def list_source_names(
        cls,
        provider: SourceProvider | None = None,
    ) -> list[str]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseSource] = list(cls.sources.values())
        _results: list[str] = []
        for _s in _snapshot:
            if provider is None or _s.provider == provider:
                _results.append(_s.name)
        return _results

    @classmethod
    def list_sources(
        cls,
        provider: SourceProvider | None = None,
    ) -> list[BaseSource]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseSource] = list(cls.sources.values())
        _results: list[BaseSource] = []
        for _s in _snapshot:
            if provider is None or _s.provider == provider:
                _results.append(_s)
        return _results

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.sources = None
