from __future__ import annotations

import threading
from pathlib import Path

from app.internal.util.path import IPath
from app.setting.service import ServicesSetting
from app.setting.system import SystemSetting


class GlobalSetting:
    """
    Global setting resource manager.

    Attributes:
    ----------
        setting_path (Path | None):
            Global setting path
        system_file_name (str):
            System setting file name
        system_setting_path (Path | None):
            System setting path
        system_setting (SystemSetting | None):
            System setting instance
        services_file_name (str):
            Services setting file name
        services_setting_path (Path | None):
            Services setting path, None when the file does not exist
        services_setting (ServicesSetting | None):
            Services setting instance, defaults when the file does not exist

    Methods:
    ----------
        load(setting_path: Path | str | None = None) -> None:
            Load global setting
        get_system() -> SystemSetting:
            Get the system setting
        get_services() -> ServicesSetting:
            Get the services setting (machine, node, mcphost, webhost)
        get_setting_path() -> Path:
            Get the setting path
        reset() -> None:
            Reset the global setting manager

    Example:
    ----------
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
    services_file_name: str = "services.yaml"
    services_setting_path: Path | None = None
    services_setting: ServicesSetting | None = None

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

        # Resolve the services setting, the file is optional
        _services_file = _setting_path / cls.services_file_name
        if _services_file.exists():
            _services_setting_path = IPath.validate_yaml(value=_services_file)
            _services_setting = ServicesSetting.from_yaml(path=_services_setting_path)
        else:
            _services_setting_path = None
            _services_setting = ServicesSetting()

        # Update the class attributes
        with cls._lock:
            cls.setting_path = _setting_path
            cls.system_setting_path = _system_setting_path
            cls.system_setting = _system_setting
            cls.services_setting_path = _services_setting_path
            cls.services_setting = _services_setting

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
    def get_services(cls) -> ServicesSetting:
        with cls._lock:
            cls._ensure_loaded()
            return cls.services_setting

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
            cls.services_setting_path = None
            cls.services_setting = None
            cls.services_file_name = "services.yaml"
