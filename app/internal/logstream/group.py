from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.internal.logstream.format import FileFormat, GlbFormatFactory


class ConsoleGroup(logging.StreamHandler):
    """
    Console Group handler for standard output

    Args:
        stream (str | None):
            The stream to which the logs will be written. If None, defaults to sys.stderr.
        format (logging.Formatter | None):
            The formatter to use for the logs. If None, no formatter is set.

    Example:
        >>> handler = ConsoleGroup()
        >>> logger = logging.getLogger(__name__)
        >>> logger.addHandler(handler)

    """

    def __init__(
        self,
        stream: str | None = None,
        format: str | None = None,
    ) -> None:
        super().__init__(stream=stream)
        _instance: logging.Formatter = GlbFormatFactory.get(format)
        self.setFormatter(_instance)


class FileGroup(RotatingFileHandler):
    """
    File Group handler for local storage

    Args:
        path (str | Path):
            The path to the log file or directory. If a directory is provided, a default log file name will be used.
        name (str | None):
            The name of the log file. If None, a default name will be used.
        max_size_mb (int | None):
            The maximum size in megabytes of the log file before it is rotated. If None, a default size will be used.
        backup_count (int | None):
            The number of backup files to keep. If None, a default count will be used.

    Example:
        >>> handler = FileGroup(
        ...     path="/var/log/myapp",
        ...     name="myapp",
        ...     max_size_mb=10,
        ...     backup_count=5,
        ... )
        >>> logger = logging.getLogger(__name__)
        >>> logger.addHandler(handler)

    """

    default_name: str = "default"
    default_max_size_mb: int = 10
    default_backup_count: int = 1

    def __init__(
        self,
        path: str | Path,
        name: str | None = None,
        max_size_mb: int | None = None,
        backup_count: int | None = None,
    ) -> None:
        _name: str = self._resolve_name(name)
        _path: Path = self._resolve_path(path, _name)
        _max_bytes: int = self._resolve_max_bytes(max_size_mb)
        _backup_count: int = self._resolve_backup_count(backup_count)
        super().__init__(
            str(_path),
            encoding="utf-8",
            maxBytes=_max_bytes,
            backupCount=_backup_count,
        )
        self._name: str = _name
        self._path: Path = _path
        self._max_bytes: int = _max_bytes
        self._backup_count: int = _backup_count
        self._date_format: str = "%Y-%m-%dT%H:%M:%S%z"
        self._format = FileFormat()
        self.setFormatter(self._format)

    def _resolve_name(
        self,
        name: str | None = None,
    ) -> str:
        return name or self.default_name

    def _resolve_path(
        self,
        path: str | Path,
        name: str | None = None,
    ) -> Path:
        _path: Path = Path(path)
        if not _path.parent.exists():
            _path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        if _path.is_dir():
            _path: Path = _path / f"{name}.log"
        return _path.expanduser().resolve()

    def _resolve_max_bytes(
        self,
        value: int | None,
    ) -> int:
        return (value or self.default_max_size_mb) * 1024 * 1024

    def _resolve_backup_count(
        self,
        value: int | None,
    ) -> int:
        return value or self.default_backup_count

    def emit(
        self,
        event: logging.LogRecord,
    ):
        try:
            super().emit(event)
        except Exception as e:
            self.handleError(event)
            raise e
