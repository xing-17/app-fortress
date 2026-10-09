from __future__ import annotations

import threading

from app.internal.logstream import LogStream
from app.resource._global.setting import GlobalSetting
from app.setting._log import LogSetting
from app.setting.system import SystemSetting


class GlobalLogStreams:
    """
    Global LogStream resource manager.

    Attributes:
    ----------
        streams (dict[str, LogStream] | None):
            Global LogStream dict, keyed by LogStream name, valued by LogStream instance
        system (LogStream | None):
            Default LogStream instance, taken from the system setting's log configuration
        _lock (threading.RLock):
            Thread lock, used to ensure thread safety

    Methods:
    ----------
        load() -> None:
            Load global LogStreams from the system setting
        get_system() -> LogStream:
            Get the default LogStream
        add_stream(setting: LogSetting) -> LogStream:
            Register a new LogStream; raises if the name already exists
        get_stream(name: str, strict: bool = False) -> LogStream | None:
            Get the LogStream with the given name; raises if missing and strict is True
        resolve(value: LogStream | LogSetting | str | None, default: LogStream) -> LogStream:
            Resolve the given instance/setting/name/None into a concrete LogStream instance, without registering it into the global dict
        list_stream_names() -> list[str]:
            List all LogStream names
        list_streams() -> list[LogStream]:
            List all LogStream instances
        reset() -> None:
            Reset the global LogStream manager

    Example:
    ----------
        >>> from app.resource._global.logstreams import GlobalLogStreams
        >>> system_stream = GlobalLogStreams.get_system()
        >>> all_stream_names = GlobalLogStreams.list_stream_names()
        >>> all_streams = GlobalLogStreams.list_streams()

    """

    streams: dict[str, LogStream] | None = None
    system: LogStream | None = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def load(cls) -> None:
        _sys_setting: SystemSetting = GlobalSetting.get_system()
        _sys_log_setting: LogSetting = _sys_setting.log
        try:
            _sys_log: LogStream = LogStream.from_setting(_sys_log_setting)
            _sys_log_name: str = _sys_log.name
        except Exception as e:
            raise ValueError(f"Failed to load log stream: {e}") from e
        with cls._lock:
            cls.streams = {_sys_log_name: _sys_log}
            cls.system = _sys_log

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.streams is not None:
            return
        with cls._lock:
            if cls.streams is None:
                cls.load()

    @classmethod
    def get_system(cls) -> LogStream:
        with cls._lock:
            cls._ensure_loaded()
            return cls.system

    @classmethod
    def add_stream(
        cls,
        setting: LogSetting,
    ) -> LogStream:
        with cls._lock:
            cls._ensure_loaded()
            _name: str = setting.name
            if _name in cls.streams:
                raise ValueError(f"Duplicate log stream entry '{_name}'")
            try:
                cls.streams[_name] = LogStream.from_setting(setting)
            except Exception as e:
                raise ValueError(f"Failed to add log stream '{_name}': {e}") from e
            return cls.streams[_name]

    @classmethod
    def resolve(
        cls,
        value: LogStream | LogSetting | str | None,
        default: LogStream,
    ) -> LogStream:
        if isinstance(value, LogStream):
            _res: LogStream = value
        elif value is None:
            if not isinstance(default, LogStream):
                raise ValueError(f"Default must be type 'LogStream', got {type(default)}")
            _res: LogStream = default
        elif isinstance(value, LogSetting):
            _res: LogStream = LogStream.from_setting(value)
        elif isinstance(value, str):
            _res: LogStream = cls.get_stream(value, strict=True)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

        return _res

    @classmethod
    def get_stream(
        cls,
        name: str,
        strict: bool = False,
    ) -> LogStream | None:
        with cls._lock:
            cls._ensure_loaded()
            if strict and name not in cls.streams:
                raise ValueError(f"Log stream '{name}' not found")
            return cls.streams.get(name)

    @classmethod
    def list_stream_names(cls) -> list[str]:
        with cls._lock:
            cls._ensure_loaded()
            return list(cls.streams.keys())

    @classmethod
    def list_streams(cls) -> list[LogStream]:
        with cls._lock:
            cls._ensure_loaded()
            return list(cls.streams.values())

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.streams = None
            cls.system = None
