from __future__ import annotations

import threading

from app.internal.constant.platform import Platform
from app.resource._global.setting import GlobalSetting
from app.resource.store._common._base import BaseStore
from app.resource.store._common._factory import StoreFactory
from app.setting._store import UnionStoreSetting
from app.setting.system import SystemSetting


class GlobalStores:
    """
    全局Store类资源管理

    Attributes:
        stores (dict[str, BaseStore] | None):
            全局Store字典，键为Store名称，值为Store实例
        _lock (threading.RLock):
            线程锁，用于保证线程安全

    Methods:
        load() -> None:
            加载全局Store
        get_store(name: str) -> BaseStore:
            获取指定名称的Store
        resolve(value: BaseStore | str | None, default: BaseStore, platform: Platform | None = None) -> BaseStore:
            将传入的实例/名称/None解析为具体的Store实例，不会注册进全局字典
        list_store_names(platform: Platform | None = None) -> list[str]:
            列出所有Store的名称
        list_stores(platform: Platform | None = None) -> list[BaseStore]:
            列出所有Store实例
        reset() -> None:
            重置全局Store管理器

    Examples:
        >>> from app.resource._global.stores import GlobalStores
        >>> all_store_names = GlobalStores.list_store_names()
        >>> all_stores = GlobalStores.list_stores()

    """

    stores: dict[str, BaseStore] | None = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls) -> None:
        _stores: dict[str, BaseStore] = {}
        _sys_setting: SystemSetting = GlobalSetting.get_system()
        _store_settings: list[UnionStoreSetting] = _sys_setting.stores
        for _store_setting in _store_settings:
            _name: str = _store_setting.name
            if _name in _stores:
                raise ValueError(f"Duplicate store entry '{_name}'")
            try:
                _stores[_name] = StoreFactory.load(_store_setting)
            except Exception as e:
                raise ValueError(f"Failed to load store '{_name}': {e}") from e
        with cls._lock:
            cls.stores = _stores

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.stores is not None:
            return
        with cls._lock:
            if cls.stores is None:
                cls.load()

    @classmethod
    def get_store(
        cls,
        name: str,
        strict: bool = True,
    ) -> BaseStore:
        with cls._lock:
            cls._ensure_loaded()
            if strict and name not in cls.stores:
                raise ValueError(f"Store '{name}' not found")
            return cls.stores.get(name)

    @classmethod
    def resolve(
        cls,
        value: BaseStore | str | None,
        default: BaseStore,
        platform: Platform | None = None,
    ) -> BaseStore:
        if isinstance(value, BaseStore):
            _res: BaseStore = value
        elif value is None:
            if not isinstance(default, BaseStore):
                raise ValueError(f"Default must be type 'BaseStore', got {type(default)}")
            _res: BaseStore = default
        elif isinstance(value, str):
            _res: BaseStore = cls.get_store(value, strict=True)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        if platform and _res.platform != platform:
            raise ValueError(f"Store '{_res.name}' does not match platform '{platform}'")

        return _res

    @classmethod
    def list_store_names(
        cls,
        platform: Platform | None = None,
    ) -> list[str]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseStore] = list(cls.stores.values())
        _result: list[str] = []
        for _s in _snapshot:
            if platform is None or _s.platform == platform:
                _result.append(_s.name)
        return _result

    @classmethod
    def list_stores(
        cls,
        platform: Platform | None = None,
    ) -> list[BaseStore]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseStore] = list(cls.stores.values())
        _result: list[BaseStore] = []
        for _s in _snapshot:
            if platform is None or _s.platform == platform:
                _result.append(_s)
        return _result

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.stores = None
