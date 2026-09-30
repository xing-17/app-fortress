from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from app.internal.logstream.event import LogEvent
from app.internal.logstream.group import ConsoleGroup, FileGroup
from app.internal.util.clock import IClock
from app.internal.util.timezone import ITimezone
from app.setting._log import LogSetting


class LogStream(logging.Logger):
    """
    Events log stream for structured logging.

    Args:
        name (str):
            The name of the logger.
        level (str | None):
            The logging level for the logger. Default is "INFO".
        timezone (ZoneInfo | str | None):
            The timezone for the logger. If None, defaults to UTC.
        metadata (dict[str, Any] | None):
            Additional metadata to include in log events. Default is None.
        tags (dict[str, str] | None):
            Additional tags to include in log events. Default is None.
        console_format (str | None):
            The format for the console output. If None, defaults to a standard format.
        file_path (str | Path | None):
            The path to the log file. If None, file logging is disabled.
        file_max_items (int | None):
            The maximum number of log items to keep in the file buffer. If None, defaults to 100,000.

    Example:
        >>> logger = LogStream(
        ...     name="my_logger",
        ...     level="DEBUG",
        ...     timezone="UTC",
        ...     metadata={"app": "my_app"},
        ...     tags={"env": "production"},
        ... )
        >>> logger.info("This is an info message.")
        >>> logger.error("This is an error message.")

    """

    _default_name: str = "default"
    _default_level: str = "INFO"

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        # logging.Logger isn't a pydantic model; only accept existing instances
        # (no dict-based construction, no automatic serialization).
        return core_schema.is_instance_schema(cls)

    @classmethod
    def from_setting(
        cls,
        setting: LogSetting,
    ) -> LogStream:
        return cls(
            name=setting.name,
            level=setting.level,
            timezone=setting.timezone,
            metadata=setting.metadata,
            tags=setting.tags,
            console_verbose=setting.console_verbose,
            console_format=setting.console_format,
            file_path=setting.file_path,
            file_max_items=setting.file_max_items,
        )

    def __init__(
        self,
        name: str | None = None,
        level: str | None = None,
        timezone: ZoneInfo | str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        console_verbose: bool = True,
        console_format: str | None = None,
        file_path: str | Path | None = None,
        file_max_items: int | None = None,
    ) -> None:
        _name: str = self._resolve_name(name)
        _level: int = self._resolve_level(level)

        # init native logger
        super().__init__(
            name=_name,
            level=_level,
        )

        # stream attributes
        self._name: str = _name
        self._level: int = _level
        self._timezone: ZoneInfo = ITimezone.resolve(timezone)
        self._metadata: dict[str, Any] = dict(metadata or {})
        self._tags: dict[str, str] = dict(tags or {})

        # console attributes
        self._console_verbose: bool = console_verbose
        self._console_format: str | None = console_format

        # file attributes
        self._file_path: str | None = file_path
        self._file_max_items: int | None = file_max_items

        # setup `handlers`
        self._console: ConsoleGroup | None = self._resolve_console()
        self._file: FileGroup | None = self._resolve_file()

    def _resolve_name(
        self,
        name: str | None = None,
    ) -> str:
        if name:
            return name.lower()
        return self._default_name

    def _resolve_level(
        self,
        level: str | None = None,
    ) -> int:
        if not level:
            level = self._default_level
        _level = level.upper()
        _mapping = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }
        return _mapping.get(_level, logging.INFO)

    def _resolve_console(self) -> ConsoleGroup | None:
        if self._console_verbose:
            _console = ConsoleGroup(self._console_format)
            self.addHandler(_console)
            return _console
        else:
            return None

    def _resolve_file(self) -> FileGroup | None:
        if self._file_path:
            _file = FileGroup(
                path=self._file_path,
                name=self._name,
                max_items=self._file_max_items,
            )
            self.addHandler(_file)
            return _file
        return None

    def _merge_dict(
        self,
        base: dict[str, Any],
        update: dict[str, Any] | None,
    ) -> dict[str, Any]:
        merged = dict(base)
        if update:
            merged.update(update)
        return merged

    def _with_event_context(
        self,
        kwargs: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        _extra = dict(kwargs.pop("extra", {}) or {})
        if metadata is not None:
            _extra["metadata"] = self._merge_dict(
                base=self._metadata,
                update=metadata,
            )
        if tags is not None:
            _extra["tags"] = self._merge_dict(
                base=self._tags,
                update=tags,
            )
        if metrics is not None:
            _extra["metrics"] = self._merge_dict(
                base={},
                update=metrics,
            )
        kwargs["extra"] = _extra
        return kwargs

    def info(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().info(msg, *args, **kwargs)

    def debug(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().debug(msg, *args, **kwargs)

    def warning(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().warning(msg, *args, **kwargs)

    def error(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().error(msg, *args, **kwargs)

    def critical(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().critical(msg, *args, **kwargs)

    def exception(
        self,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().exception(msg, *args, **kwargs)

    def log(
        self,
        level: int,
        msg: object,
        *args: Any,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, str | int | float] | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs = self._with_event_context(
            kwargs=kwargs,
            metadata=metadata,
            metrics=metrics,
            tags=tags,
        )
        super().log(level, msg, *args, **kwargs)

    def makeRecord(
        self,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args: tuple[Any, ...] | dict[str, Any],
        exc_info: tuple[type[BaseException], BaseException, object] | None,
        func: str | None = None,
        extra: dict[str, Any] | None = None,
        sinfo: str | None = None,
    ) -> LogEvent:
        _extra = dict(extra or {})
        _created_at: datetime = IClock.current(self._timezone)
        _metadata: dict[str, Any] = self._merge_dict(
            base=self._metadata,
            update=_extra.pop("metadata", {}),
        )
        _metrics: dict[str, str | int | float] = _extra.pop("metrics", {})
        _tags: dict[str, str] = self._merge_dict(
            base=self._tags,
            update=_extra.pop("tags", {}),
        )
        record = LogEvent(
            name=name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            created_at=_created_at,
            metadata=_metadata,
            metrics=_metrics,
            tags=_tags,
        )
        if _extra:
            for key, value in _extra.items():
                if key in {"message", "asctime"} or key in record.__dict__:
                    raise KeyError(f"Attempt to overwrite {key!r} in LogEvent")
                record.__dict__[key] = value
        return record

    def read(
        self,
        limit: int | None = None,
    ) -> list[dict]:
        _all_events: list[dict] = []
        if self._file:
            _all_events = self._file.read(limit=limit)
        return _all_events

    def export(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "level": self._level,
            "timezone": str(self._timezone),
            "metadata": self._metadata,
            "tags": self._tags,
            "console_verbose": self._console_verbose,
            "console_format": self._console_format,
            "file_path": self._file_path,
            "file_max_items": self._file_max_items,
        }
