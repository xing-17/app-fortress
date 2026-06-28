from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel, ValidationError

from app.common.setting.cache import CacheSetting
from app.common.setting.connections import ConnectionsSetting
from app.common.setting.system import SystemSetting


class CoreSetting(BaseModel):
    """
    应用配置聚合。

    从 YAML 文件加载并管理所有应用配置，支持运行时刷新。
    默认从项目 setting/ 目录读取各配置文件。

    Attributes:
        system[SystemSetting]: 系统运行时配置
        connections[ConnectionsSetting]: 连接配置
        cache[CacheSetting]: 缓存配置

    Examples:
        >>> setting = CoreSetting.load()
        >>> setting.describe()
        >>> setting.refresh()
        >>> print(setting.system.name)
        'fortress'

    """

    _system_path: ClassVar[Optional[Path]] = None
    _conns_path: ClassVar[Optional[Path]] = None
    _cache_path: ClassVar[Optional[Path]] = None

    _default_root_dir: ClassVar[Path] = Path(__file__).parent.parent.parent.parent
    _default_setting_dir: ClassVar[Path] = _default_root_dir / "setting"
    _default_sys_setting_path: ClassVar[Path] = _default_setting_dir / "system.yml"
    _default_conn_setting_path: ClassVar[Path] = _default_setting_dir / "connections.yml"
    _default_cache_path: ClassVar[Path] = _default_setting_dir / "cache.yml"

    system: SystemSetting
    connections: ConnectionsSetting
    cache: CacheSetting

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

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to read yaml file: {e}") from e

        if not data:
            raise ValueError(f"Yaml file is not valid: {path}")
        return data

    @classmethod
    def load(
        cls,
        system_path: str | Path | None = None,
        conns_path: str | Path | None = None,  # 新增
        cache_path: str | Path | None = None,  # 新增
    ) -> "CoreSetting":
        # Resolve and validate the system setting path
        system_path = CoreSetting._resolve_path(
            path=system_path,
            default=cls._default_sys_setting_path,
        )
        cls._validate_path(system_path)
        system_data = cls._read_yaml(system_path)

        # Resolve and validate the connections setting path
        conns_path = cls._resolve_path(
            path=conns_path,
            default=cls._default_conn_setting_path,
        )
        cls._validate_path(conns_path)
        conn_data = cls._read_yaml(conns_path)

        # Resolve and validate the cache setting path
        cache_path = cls._resolve_path(
            path=cache_path,
            default=cls._default_cache_path,
        )
        cls._validate_path(cache_path)
        cache_data = cls._read_yaml(cache_path)

        # Create an instance of CoreSetting with the loaded data
        # Add more settings here
        try:
            instance = cls(
                system=SystemSetting(**system_data),
                connections=ConnectionsSetting(**conn_data),
                cache=CacheSetting(**cache_data),
            )
            cls._system_path = system_path
            cls._conns_path = conns_path
            cls._cache_path = cache_path
            return instance
        except ValidationError as e:
            msg = f"Setting validation failed:\n{e}"
            raise ValueError(msg) from e

    def refresh(self) -> None:
        # Resolve and validate the system setting path
        system_path = self.__class__._system_path
        CoreSetting._validate_path(system_path)
        system_data = CoreSetting._read_yaml(system_path)

        # Resolve and validate the connections setting path
        conn_path = self.__class__._conns_path
        CoreSetting._validate_path(conn_path)
        conn_data = CoreSetting._read_yaml(conn_path)

        # Resolve and validate the cache setting path
        cache_path = self.__class__._cache_path
        CoreSetting._validate_path(cache_path)
        cache_data = CoreSetting._read_yaml(cache_path)

        try:
            temp = self.__class__(
                system=SystemSetting(**system_data),
                connections=ConnectionsSetting(**conn_data),
                cache=CacheSetting(**cache_data),
            )
            self.system = temp.system
            self.connections = temp.connections
            self.cache = temp.cache
        except ValidationError as e:
            raise ValueError(f"Setting validation failed:\n{e}") from e

    def export(self) -> dict:
        return {
            "system": self.system.export(),
            "connections": self.connections.export(),
            "cache": self.cache.export(),
        }

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
