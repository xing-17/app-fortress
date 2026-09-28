from __future__ import annotations

import threading

from app.internal.logstream import LogStream
from app.resource._global.setting import GlobalSetting
from app.setting._log import LogSetting
from app.setting.system import SystemSetting


class GlobalLogStreams:
    """
    全局LogStream类资源管理

    Attributes:
        streams (dict[str, LogStream] | None):
            全局LogStream字典，键为LogStream名称，值为LogStream实例
        system (LogStream | None):
            默认LogStream实例，取自系统设置中的日志配置
        _lock (threading.RLock):
            线程锁，用于保证线程安全

    Methods:
        load() -> None:
            加载全局LogStream
        get_system() -> LogStream:
            获取默认LogStream
        add_stream(setting: LogSetting) -> LogStream:
            新增一个LogStream
        get_stream(name: str, strict: bool = False) -> LogStream | None:
            获取指定名称的LogStream
        resolve(value: LogStream | LogSetting | str | None, default: LogStream) -> LogStream:
            将传入的实例/LogSetting/名称/None解析为具体的LogStream实例，不会注册进全局字典
        list_stream_names() -> list[str]:
            列出所有LogStream的名称
        list_streams() -> list[LogStream]:
            列出所有LogStream实例
        reset() -> None:
            重置全局LogStream管理器

    Examples:
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
            _name: str = setting.name.lower()
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
            _name: str = name.lower()
            if strict and _name not in cls.streams:
                raise ValueError(f"Log stream '{_name}' not found")
            return cls.streams.get(_name)

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
