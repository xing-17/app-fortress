from __future__ import annotations

import threading

from app.internal.constant.platform import Platform
from app.resource._global.setting import GlobalSetting
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity._common._factory import IdentityFactory
from app.setting._identity import UnionIdentitySetting
from app.setting.system import SystemSetting


class GlobalIdentities:
    """
    全局Identity类资源管理

    Attributes:
        identities (dict[str, BaseIdentity] | None):
            全局Identity字典，键为Identity名称，值为Identity实例
        _lock (threading.RLock):
            线程锁，用于保证线程安全

    Methods:
        load() -> None:
            加载全局Identity
        get_identity(name: str, strict: bool = False) -> BaseIdentity | None:
            获取指定名称的Identity
        list_identity_names(platform: Platform | None = None) -> list[str]:
            列出所有Identity的名称
        list_identities(platform: Platform | None = None) -> list[BaseIdentity]:
            列出所有Identity实例
        reset() -> None:
            重置全局Identity管理器

    Examples:
        >>> from app.resource._global.identities import GlobalIdentities
        >>> all_identity_names = GlobalIdentities.list_identity_names()
        >>> all_identities = GlobalIdentities.list_identities()

    """

    identities: dict[str, BaseIdentity] | None = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls) -> None:
        _identities: dict[str, BaseIdentity] = {}
        _sys_setting: SystemSetting = GlobalSetting.get_system()
        _idt_settings: list[UnionIdentitySetting] = _sys_setting.identities
        for _idt_setting in _idt_settings:
            _name: str = _idt_setting.name
            if _name in _identities:
                raise ValueError(f"Duplicate identity entry '{_name}'")
            try:
                _identities[_name] = IdentityFactory.load(_idt_setting)
            except Exception as e:
                raise ValueError(f"Failed to load identity '{_name}': {e}") from e
        with cls._lock:
            cls.identities = _identities

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.identities is not None:
            return
        with cls._lock:
            if cls.identities is None:
                cls.load()

    @classmethod
    def get_identity(
        cls,
        name: str,
        strict: bool = False,
    ) -> BaseIdentity | None:
        with cls._lock:
            cls._ensure_loaded()
            if strict and name not in cls.identities:
                raise ValueError(f"Identity '{name}' not found")
            return cls.identities.get(name)

    @classmethod
    def resolve(
        cls,
        value: BaseIdentity | str | None,
        platform: Platform,
        default: BaseIdentity,
    ) -> BaseIdentity | None:
        if isinstance(value, BaseIdentity):
            _res: BaseIdentity = value
        elif value is None:
            _res: BaseIdentity = default
        elif isinstance(value, str):
            _res: BaseIdentity = cls.get_identity(value, strict=True)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        if _res.platform != platform:
            raise ValueError(f"Identity '{_res.name}' does not match platform '{platform}'")

        return _res

    @classmethod
    def list_identity_names(
        cls,
        platform: Platform | None = None,
    ) -> list[str]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseIdentity] = list(cls.identities.values())
        _result: list[str] = []
        for i in _snapshot:
            if platform is None or i.platform == platform:
                _result.append(i.name)
        return _result

    @classmethod
    def list_identities(
        cls,
        platform: Platform | None = None,
    ) -> list[BaseIdentity]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot = list(cls.identities.values())
        _result: list[BaseIdentity] = []
        for i in _snapshot:
            if platform is None or i.platform == platform:
                _result.append(i)
        return _result

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.identities = None
