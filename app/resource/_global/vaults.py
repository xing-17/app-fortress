from __future__ import annotations

import threading

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.resource._global.setting import GlobalSetting
from app.resource.asset._common._factory import VaultFactory
from app.resource.asset._common._vault import BaseVault
from app.setting._vault import AbstractVaultSetting, UnionVaultSetting
from app.setting.system import SystemSetting


class GlobalVaults:
    """
    全局Vault类资源管理

    Attributes:
        vaults (dict[str, BaseVault] | None):
            全局Vault字典，键为Vault名称，值为Vault实例
        _lock (threading.RLock):
            线程锁，用于保证线程安全

    Methods:
        load() -> None:
            加载全局Vault
        get_vault(name: str) -> BaseVault:
            获取指定名称的Vault
        resolve(value: BaseVault | str | None, default: BaseVault, filesystem: AssetFilesystem | None = None) -> BaseVault:
            将传入的实例/名称/None解析为具体的Vault实例，不会注册进全局字典
        reset() -> None:
            重置全局Vault管理器

    Examples:
        >>> from app.resource._global.vaults import GlobalVaults
        >>> vault = GlobalVaults.get_vault("my_vault")

    """

    vaults: dict[str, BaseVault] | None = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls) -> None:
        _vaults: dict[str, BaseVault] = {}
        _sys_setting: SystemSetting = GlobalSetting.get_system()
        _vault_settings: list[UnionVaultSetting] = _sys_setting.vaults
        for _vault_setting in _vault_settings:
            _name: str = _vault_setting.name
            if _name in _vaults:
                raise ValueError(f"Duplicate vault entry '{_name}'")
            try:
                _vaults[_name] = VaultFactory.load(_vault_setting)
            except Exception as e:
                raise ValueError(f"Failed to load vault '{_name}': {e}") from e
        with cls._lock:
            cls.vaults = _vaults

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.vaults is not None:
            return
        with cls._lock:
            if cls.vaults is None:
                cls.load()

    @classmethod
    def get_vault(
        cls,
        name: str,
        strict: bool = True,
    ) -> BaseVault | None:
        with cls._lock:
            cls._ensure_loaded()
            if strict and name not in cls.vaults:
                raise ValueError(f"Vault '{name}' not found")
            return cls.vaults.get(name)

    @classmethod
    def resolve(
        cls,
        value: BaseVault | UnionVaultSetting | str | None,
        default: BaseVault,
        filesystem: AssetFilesystem | None = None,
    ) -> BaseVault:
        if isinstance(value, BaseVault):
            _res: BaseVault = value
        elif value is None:
            if not isinstance(default, BaseVault):
                raise ValueError(f"Default must be type 'BaseVault', got {type(default)}")
            _res: BaseVault = default
        elif isinstance(value, str):
            _res: BaseVault = cls.get_vault(value, strict=True)
        elif isinstance(value, AbstractVaultSetting):
            _res: BaseVault = VaultFactory.load(value)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        if filesystem and _res.filesystem != filesystem:
            raise ValueError(f"Vault '{_res.name}' does not match filesystem '{filesystem}'")

        return _res

    @classmethod
    def list_vault_names(
        cls,
        filesystem: AssetFilesystem | None = None,
    ) -> list[str]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseVault] = list(cls.vaults.values())
        _results: list[BaseVault] = []
        for _v in _snapshot:
            if filesystem is None or _v.filesystem == filesystem:
                _results.append(_v.name)
        return _results

    @classmethod
    def list_vaults(
        cls,
        filesystem: AssetFilesystem | None = None,
    ) -> list[BaseVault]:
        with cls._lock:
            cls._ensure_loaded()
            _snapshot: list[BaseVault] = list(cls.vaults.values())
        _results: list[BaseVault] = []
        for _v in _snapshot:
            if filesystem is None or _v.filesystem == filesystem:
                _results.append(_v)
        return _results

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.vaults = None
