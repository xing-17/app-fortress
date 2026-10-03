from __future__ import annotations

import threading

from app.internal.constant.platform import Platform
from app.resource._global.setting import GlobalSetting
from app.resource.identity._common._factory import IdentityFactory
from app.resource.identity._common._identity import BaseIdentity
from app.setting._identity import AbstractIdentitySetting, UnionIdentitySetting
from app.setting.system import SystemSetting


class GlobalIdentities:
    """
    Global Identity resource manager.

    Attributes:
        identities (dict[str, BaseIdentity] | None):
            Global Identity dict, keyed by Identity name, valued by Identity instance
        _lock (threading.RLock):
            Thread lock, used to ensure thread safety

    Methods:
        load() -> None:
            Load global Identities
        get_identity(name: str, strict: bool = False) -> BaseIdentity | None:
            Get the Identity with the given name
        resolve(value: BaseIdentity | str | None, default: BaseIdentity, platform: Platform | None = None) -> BaseIdentity | None:
            Resolve the given instance/name/None into a concrete Identity instance, without registering it into the global dict
        list_identity_names(platform: Platform | None = None) -> list[str]:
            List all Identity names
        list_identities(platform: Platform | None = None) -> list[BaseIdentity]:
            List all Identity instances
        reset() -> None:
            Reset the global Identity manager

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
        value: BaseIdentity | UnionIdentitySetting | str | None,
        default: BaseIdentity,
        platform: Platform | None = None,
    ) -> BaseIdentity | None:
        if isinstance(value, BaseIdentity):
            _res: BaseIdentity = value
        elif value is None:
            if not isinstance(default, BaseIdentity):
                raise ValueError(f"Default must be type 'BaseIdentity', got {type(default)}")
            _res: BaseIdentity = default
        elif isinstance(value, str):
            _res: BaseIdentity = cls.get_identity(value, strict=True)
        elif isinstance(value, AbstractIdentitySetting):
            _res: BaseIdentity = IdentityFactory.load(value)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        if platform and _res.platform != platform:
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
