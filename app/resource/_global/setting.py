from __future__ import annotations

import threading
from pathlib import Path

from app.internal.util.path import IPath
from app.setting.system import SystemSetting


class GlobalSetting:
    """

    全局设置管理

    Attributes:
        setting_path (Path | None):
            全局设置路径
        system_file_name (str):
            系统设置文件名
        system_setting_path (Path | None):
            系统设置路径
        system_setting (SystemSetting | None):
            系统设置实例

    Methods:
        load(setting_path: Path | str | None = None) -> None:
            加载全局设置
        get_system() -> SystemSetting:
            获取系统设置
        get_setting_path() -> Path:
            获取设置路径

    Examples:
        >>> from app.resource._global.setting import GlobalSetting
        >>> system_setting = GlobalSetting.get_system()
        >>> setting_path = GlobalSetting.get_setting_path()

    """

    _default_app_path = Path(__file__).parent.parent.parent.parent
    _default_setting_path = _default_app_path / "settings"

    # Resetable attributes
    setting_path: Path | None = None
    system_file_name: str = "system.yaml"
    system_setting_path: Path | None = None
    system_setting: SystemSetting | None = None

    # thread lock
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls, setting_path: Path | str | None = None) -> None:
        # Resolve the setting path
        _setting_path = IPath.resolve(
            value=setting_path,
            default=cls._default_setting_path,
            validate=True,
        )

        # Resolve the system setting path and system setting
        _system_setting_path = IPath.validate_yaml(
            value=_setting_path / cls.system_file_name,
        )
        _system_setting = SystemSetting.from_yaml(
            path=_system_setting_path,
        )

        # Update the class attributes
        with cls._lock:
            cls.setting_path = _setting_path
            cls.system_setting_path = _system_setting_path
            cls.system_setting = _system_setting

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.system_setting is not None:
            return
        with cls._lock:
            if cls.system_setting is None:
                cls.load()

    @classmethod
    def get_system(cls) -> SystemSetting:
        with cls._lock:
            cls._ensure_loaded()
            return cls.system_setting

    @classmethod
    def get_setting_path(cls) -> Path:
        with cls._lock:
            cls._ensure_loaded()
            return cls.setting_path

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.setting_path = None
            cls.system_setting_path = None
            cls.system_setting = None
            cls.system_file_name = "system.yaml"
