from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from app.internal.logstream.format import FileFormat, GlbFormatFactory


class ConsoleGroup(logging.StreamHandler):
    """
    Console Group handler for standard output

    Args:
        format (logging.Formatter | None):
            The formatter to use for the logs. If None, no formatter is set.

    """

    def __init__(
        self,
        format: str | None = None,
    ) -> None:
        super().__init__(stream=sys.stdout)
        _instance: logging.Formatter = GlbFormatFactory.get(format)
        self.setFormatter(_instance)


class FileGroup(logging.Handler):
    """
    File Group handler for local storage

    Args:
        path (str | Path):
            The folder to store the log file in. Must be a directory, not a file path.
        name (str | None):
            The name of the log file. If None, a default name will be used.
        max_items (int | None):
            The maximum number of log items to keep, default is 100_000.

    Raises:
        ValueError: If `path` points to an existing file rather than a directory.
        ValueError: If `max_items` is provided and is not a positive integer.

    Attributes:
        default_name (str):
            The default name for the log file if none is provided. Default is "default".
        default_max_items (int):
            The default maximum number of log items to keep in the log file. Default is 100_000.

    Methods:
        emit(event: logging.LogRecord) -> None:
            Formats the event and appends it as a line to the log file, compacting the
            file once the item threshold is exceeded.
        read(limit: int | None = None) -> list[dict]:
            Reads log events from the log file, newest first, skipping malformed
            lines. If `limit` is given, only the `limit` most recent events are returned.

    Examples:
        >>> file_group = FileGroup(path="/var/log/myapp", name="app")
        >>> file_group.emit(log_event)
        >>> logs = file_group.read(limit=10)

    """

    default_name: str = "default"
    default_max_items: int = 100_000

    def __init__(
        self,
        path: str | Path,
        name: str | None = None,
        max_items: int | None = None,
    ) -> None:
        super().__init__()
        self._name: str = self._resolve_name(name)
        self._path: Path = self._resolve_path(path)
        self._max_items: int = self._resolve_max_items(max_items)
        self._threshold: int = max(self._max_items + 1, int(self._max_items * 1.1))
        self._n_lines: int = self._count()
        self._format: logging.Formatter = FileFormat()
        self.setFormatter(self._format)

    def _resolve_name(
        self,
        name: str | None = None,
    ) -> str:
        if name:
            return name.lower()
        return self.default_name

    def _resolve_path(
        self,
        path: str | Path,
    ) -> Path:
        _path: Path = Path(path).expanduser()
        if _path.is_file():
            raise ValueError("path must be a directory, not a file.")
        _path.mkdir(
            parents=True,
            exist_ok=True,
        )
        _path: Path = (_path / f"{self._name}.log").resolve()
        return _path

    def _resolve_max_items(
        self,
        value: int | None,
    ) -> int:
        if value is not None and value <= 0:
            raise ValueError("max_items must be a positive integer.")
        if value is None:
            return self.default_max_items
        return value

    def _count(self) -> int:
        if not self._path.exists():
            return 0
        with self._path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def _tail(
        self,
        limit: int | None = None,
    ) -> list[str]:
        if not self._path.exists():
            return []
        if limit is not None and limit <= 0:
            return []
        with self._path.open("r", encoding="utf-8") as f:
            if limit is not None:
                return f.readlines()[-(limit):]
            else:
                return f.readlines()

    def emit(
        self,
        event: logging.LogRecord,
    ) -> None:
        try:
            _line = self.format(event)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(_line)
                f.write("\n")
            self._n_lines += 1
            if self._n_lines >= self._threshold:
                self._compact()
        except Exception:
            self.handleError(event)

    def _compact(self) -> None:
        _lines = self._tail(limit=self._max_items)
        _path_suffix = self._path.suffix
        _temp = self._path.with_suffix(f"{_path_suffix}.tmp")
        with _temp.open("w", encoding="utf-8") as f:
            f.writelines(_lines)
        _temp.replace(self._path)
        self._n_lines = len(_lines)

    def read(
        self,
        limit: int | None = None,
    ) -> list[dict]:
        if not self._path.exists():
            return []
        _lines = self._tail(limit=limit)
        _result: list[dict] = []
        for line in _lines:
            try:
                _result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        _result.reverse()
        return _result
