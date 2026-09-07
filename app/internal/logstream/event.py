from __future__ import annotations

from datetime import datetime
from logging import LogRecord
from typing import Any


class LogEvent(LogRecord):
    """
    Event record representation.

    Args:
        name: (str) from LogRecord, name of the logger.
        level: (int) from LogRecord, numeric level of message (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        created_at: (datetime) the datetime when the log event was created.
        lineno: (int) from LogRecord, the line number in source file.
        pathname: (str) from LogRecord, the full pathname of the source file.
        msg: (str) from LogRecord, the message.
        args: (tuple) from LogRecord, the arguments to be merged into msg (if any).
        exc_info: (tuple | None) from LogRecord, exception information.
        metadata: (dict | None) additional metadata associated with the log event.
        tags: (dict | None) additional tags associated with the log event.

    Example:
        >>> event = LogEvent(
        ...     name="my_logger",
        ...     level=logging.INFO,
        ...     lineno=42,
        ...     pathname="/path/to/my_module.py",
        ...     created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
        ...     metadata={'user_id': 123, 'session_id': 'abc123'},
        ...     tags={'module': 'my_module', 'function': 'my_function'},
        ... )
        >>> event.created_at
        datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        >>> event.metadata
        {'user_id': 123, 'session_id': 'abc123'}
        >>> event.tags
        {'module': 'my_module', 'function': 'my_function'}

    """

    def __init__(
        self,
        name: str,
        level: int,
        created_at: datetime,
        pathname: str,
        lineno: int,
        msg: str,
        args: tuple,
        exc_info: tuple | None = None,
        metadata: dict | None = None,
        metrics: dict | None = None,
        tags: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            name=name,
            level=level,
            pathname=pathname,
            lineno=lineno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            **kwargs,
        )
        self.created_at: datetime = created_at
        self.metadata: dict = dict(metadata or {})
        self.metrics: dict = dict(metrics or {})
        self.tags: dict = dict(tags or {})

    def export(self) -> dict[str, Any]:
        _cdt_fmt: str = "%Y-%m-%dT%H:%M:%S%z"
        _cdt_str: str = self.created_at.strftime(_cdt_fmt)
        _msg: str = self.getMessage()
        _exc: dict[str, str] | None = None
        _exc_info = getattr(self, "exc_info", None)
        if _exc_info is not None:
            _type, _value, _ = _exc_info
            _exc = {
                "type": _type.__qualname__,
                "value": str(_value),
            }
        return {
            "level": self.levelname,
            "created_at": _cdt_str,
            "msg": _msg,
            "exc_info": _exc,
            "metadata": self.metadata,
            "metrics": self.metrics,
            "tags": self.tags,
        }
