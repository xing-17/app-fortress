from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel, ValidationError

from app.common.setting.cache import CacheSetting
from app.common.setting.connections import BaseConnectionSetting, ConnectionsSetting
from app.common.setting.system import SystemSetting
from app.common.setting.centre import CentreSetting
from app.common.setting.providers import ProvidersSetting, BaseProviderSetting


class CoreSetting(BaseModel):
    """
    应用配置聚合。

    从 YAML 文件加载并管理所有应用配置，支持运行时刷新。
    默认从项目 setting/ 目录读取各配置文件。

    Attributes:
        system[SystemSetting]: 系统运行时配置
        cache[CacheSetting]: 缓存配置
        connections[ConnectionsSetting]: 连接配置
        centre[CentreSetting]: 中心配置
        providers[ProvidersSetting]: 提供者配置

    Examples:
        >>> setting = CoreSetting.load()
        >>> setting.describe()
        >>> setting.refresh()
        >>> print(setting.system.name)
        'fortress'

    """
    
    # 运行时配置文件路径缓存
    _system_path: ClassVar[Optional[Path]] = None
    _cache_path: ClassVar[Optional[Path]] = None
    _centre_path: ClassVar[Optional[Path]] = None
    _conns_path: ClassVar[Optional[Path]] = None
    _providers_path: ClassVar[Optional[Path]] = None
    
    # 默认配置文件路径
    _default_root_dir: ClassVar[Path] = Path(__file__).parent.parent.parent.parent
    _default_setting_dir: ClassVar[Path] = _default_root_dir / "setting"
    _default_cache_path: ClassVar[Path] = _default_setting_dir / "cache.yml"
    _default_sys_setting_path: ClassVar[Path] = _default_setting_dir / "system.yml"
    _default_centre_setting_path: ClassVar[Path] = _default_setting_dir / "centre.yml"
    _default_providers_setting_path: ClassVar[Path] = _default_setting_dir / "providers.yml"
    _default_conn_setting_path: ClassVar[Path] = _default_setting_dir / "connections.yml"

    # 配置项
    system: SystemSetting
    cache: CacheSetting
    centre: CentreSetting
    connections: ConnectionsSetting
    providers: ProvidersSetting

    @staticmethod
    def _resolve_path(
        path: str | Path | None = None,
        default: Path | None = None,
    ) -> Path:
        if path is None:
            return default
        return Path(path).expanduser().resolve()

    @staticmethod
    def _validate_path(path: Path) -> None:
        if not path:
            raise ValueError(f"Setting path not valid: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Setting path not found: {path}")

    @classmethod
    def load(
        cls,
        system_path: str | Path | None = None,
        cache_path: str | Path | None = None,
        centre_path: str | Path | None = None,
        providers_path: str | Path | None = None,
        conns_path: str | Path | None = None,
    ) -> "CoreSetting":
        # Resolve and validate the system setting path
        system_path = CoreSetting._resolve_path(
            path=system_path,
            default=cls._default_sys_setting_path,
        )
        cls._validate_path(system_path)
        _system: SystemSetting = SystemSetting.from_yaml(system_path)
        
        # Resolve and validate the cache setting path
        cache_path = cls._resolve_path(
            path=cache_path,
            default=cls._default_cache_path,
        )
        cls._validate_path(cache_path)
        _cache: CacheSetting = CacheSetting.from_yaml(cache_path)

        # Resolve and validate the connections setting path
        conns_path = cls._resolve_path(
            path=conns_path,
            default=cls._default_conn_setting_path,
        )
        cls._validate_path(conns_path)
        _conns: ConnectionsSetting = ConnectionsSetting.from_yaml(conns_path)

        # Resolve and validate the centre setting path
        centre_path = cls._resolve_path(
            path=centre_path,
            default=cls._default_centre_setting_path,
        )
        cls._validate_path(centre_path)
        _centre: CentreSetting = CentreSetting.from_yaml(centre_path)
        
        # Resolve and validate the providers setting path
        providers_path = cls._resolve_path(
            path=providers_path,
            default=cls._default_providers_setting_path,
        )
        cls._validate_path(providers_path)
        _providers: ProvidersSetting = ProvidersSetting.from_yaml(providers_path)
        
        # Create an instance of CoreSetting with the loaded data
        try:
            instance = cls(
                system=_system,
                connections=_conns,
                cache=_cache,
                centre=_centre,
                providers=_providers,
            )
            cls._system_path = system_path
            cls._conns_path = conns_path
            cls._cache_path = cache_path
            cls._centre_path = centre_path
            cls._providers_path = providers_path
            return instance
        except ValidationError as e:
            msg = f"Setting validation failed:\n{e}"
            raise ValueError(msg) from e

    def refresh(self) -> None:
        # Resolve and validate the system setting path
        system_path = self.__class__._system_path
        CoreSetting._validate_path(system_path)
        _system: SystemSetting = SystemSetting.from_yaml(system_path)

        # Resolve and validate the connections setting path
        conn_path = self.__class__._conns_path
        CoreSetting._validate_path(conn_path)
        _conns: ConnectionsSetting = ConnectionsSetting.from_yaml(conn_path)

        # Resolve and validate the cache setting path
        cache_path = self.__class__._cache_path
        CoreSetting._validate_path(cache_path)
        _cache: CacheSetting = CacheSetting.from_yaml(cache_path)

        # Resolve and validate the centre setting path
        centre_path = self.__class__._centre_path
        CoreSetting._validate_path(centre_path)
        _centre: CentreSetting = CentreSetting.from_yaml(centre_path)
        
        # Resolve and validate the providers setting path
        providers_path = self.__class__._providers_path
        CoreSetting._validate_path(providers_path)
        _providers: ProvidersSetting = ProvidersSetting.from_yaml(providers_path)

        try:
            temp = self.__class__(
                system=_system,
                connections=_conns,
                cache=_cache,
                centre=_centre,
                providers=_providers,
            )
            self.system = temp.system
            self.connections = temp.connections
            self.cache = temp.cache
            self.centre = temp.centre
            self.providers = temp.providers
        except ValidationError as e:
            raise ValueError(f"Setting validation failed:\n{e}") from e

    def get_provider(
        self,
        name: str,
    ) -> BaseProviderSetting:
        return self.providers.get(name)
    
    def get_connection(
        self,
        name: str,
    ) -> BaseConnectionSetting:
        return self.connections.get(name)

    def export(self) -> dict:
        result = {
            "system": self.system.export(),
            "connections": self.connections.export(),
            "cache": self.cache.export(),
            "centre": self.centre.export(),
            "providers": self.providers.export(),
        }
        return result

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
# 通过调用 `CoreSetting.refresh()` 可在运行时刷新配置
GlobalSetting: CoreSetting = CoreSetting.load()
