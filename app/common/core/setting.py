from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel, ValidationError

from app.common.setting.system import SystemSetting


class CoreSetting(BaseModel):
    """
    应用配置聚合。

    从 YAML 文件加载并管理所有应用配置，支持运行时刷新。
    默认从项目 setting/ 目录读取各配置文件。

    Attributes:
        system[SystemSetting]: 系统运行时配置

    Examples:
        >>> setting = CoreSetting.load()
        >>> setting.describe()
        >>> setting.refresh()
        >>> print(setting.system.name)
        'fortress'

    """

    _system_path: ClassVar[Optional[Path]] = None
    _default_root_dir: ClassVar[Path] = Path(__file__).parent.parent.parent.parent
    _default_setting_dir: ClassVar[Path] = _default_root_dir / "setting"
    _default_sys_setting_path: ClassVar[Path] = _default_setting_dir / "system.yml"
    _default_conn_setting_path: ClassVar[Path] = _default_setting_dir / "connection.yml"

    system: SystemSetting

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
    ) -> "CoreSetting":
        # Resolve and validate the system setting path
        system_path = CoreSetting._resolve_path(
            path=system_path,
            default=CoreSetting._default_sys_setting_path,
        )
        CoreSetting._validate_path(system_path)
        system_data = CoreSetting._read_yaml(system_path)

        # Create an instance of CoreSetting with the loaded data
        # Add more settings here
        try:
            instance = cls(
                system=SystemSetting(**system_data),
            )
            cls._system_path = system_path
            return instance
        except ValidationError as e:
            msg = f"Setting validation failed:\n{e}"
            raise ValueError(msg) from e

    def refresh(self) -> None:
        # Resolve and validate the system setting path
        system_path = self.__class__._system_path
        CoreSetting._validate_path(system_path)
        system_data = CoreSetting._read_yaml(system_path)

        try:
            temp = self.__class__(
                system=SystemSetting(**system_data),
            )
            self.system = temp.system
        except ValidationError as e:
            raise ValueError(f"Setting validation failed:\n{e}") from e

    def describe(self) -> dict:
        return {
            "system": self.system.describe(),
        }


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
# 通过调用 `CoreSetting.refresh()` 可在运行时刷新配置
GlobalSetting: CoreSetting = CoreSetting.load()
