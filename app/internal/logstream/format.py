from __future__ import annotations

import json
import logging
from typing import Any

from app.internal.logstream.event import LogEvent

_COLOR_CONFIG = {
    "DEBUG": "\x1b[38;5;244m",  # grey
    "INFO": "\x1b[36m",  # Cyan
    "WARNING": "\x1b[38;5;208m",  # Orange
    "ERROR": "\x1b[31m",  # Red
    "CRITICAL": "\x1b[35m",  # Purple
}
_COLOR_RESET = "\x1b[0m"
_READABLE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_TREE_BRANCH = "├── "
_TREE_LAST = "└── "
_TREE_PIPE = "│   "
_TREE_SPACE = "    "


# Console formatters
class TreeFormat(logging.Formatter):
    """
    Tree formatter for logging.

    """

    def __init__(self) -> None:
        super().__init__()
        self._date_format = _READABLE_DATE_FORMAT

    def _render_list(
        self,
        items: list[Any],
        prefix: str,
        lines: list[str],
    ) -> None:
        for j, item in enumerate(items):
            is_last = j == len(items) - 1
            connector = _TREE_LAST if is_last else _TREE_BRANCH
            if is_last:
                child_prefix = prefix + _TREE_SPACE
            else:
                child_prefix = prefix + _TREE_PIPE
            if isinstance(item, dict):
                lines.append(f"{prefix}{connector}[{j}]:")
                self._render_dict(item, child_prefix, lines)
            elif isinstance(item, list):
                lines.append(f"{prefix}{connector}[{j}]:")
                self._render_list(item, child_prefix, lines)
            else:
                val_lines = str(item).splitlines() or [""]
                lines.append(f"{prefix}{connector}{val_lines[0]}")
                for vl in val_lines[1:]:
                    lines.append(f"{child_prefix}{vl}")

    def _render_dict(
        self,
        data: dict,
        prefix: str,
        lines: list[str],
    ) -> None:
        items = list(data.items())
        for i, (k, v) in enumerate(items):
            is_last = i == len(items) - 1
            if is_last:
                connector = _TREE_LAST
                child_prefix = prefix + _TREE_SPACE
            else:
                connector = _TREE_BRANCH
                child_prefix = prefix + _TREE_PIPE
            if isinstance(v, dict):
                lines.append(f"{prefix}{connector}{k}:")
                self._render_dict(v, child_prefix, lines)
            elif isinstance(v, list):
                lines.append(f"{prefix}{connector}{k}:")
                self._render_list(v, child_prefix, lines)
            else:
                val_lines = str(v).splitlines() or [""]
                lines.append(f"{prefix}{connector}{k}: {val_lines[0]}")
                for vl in val_lines[1:]:
                    lines.append(f"{child_prefix}{vl}")

    def format(
        self,
        record: LogEvent,
    ) -> str:
        _msg: str = record.getMessage()
        _cdt: str = record.created_at.strftime(self._date_format)
        _header = f"{_cdt} [{record.levelname}]: {_msg}"
        _indent = _TREE_SPACE
        _serial: dict[str, Any] = record.export()
        _serial.pop("msg")
        _serial.pop("level")
        _serial.pop("created_at")
        _empty_vals = [None, {}, []]
        _serial: dict[str, Any] = {k: v for k, v in _serial.items() if v not in _empty_vals}
        lines = [_header]
        for i, (key, value) in enumerate(_serial.items()):
            is_last = i == len(_serial) - 1
            if is_last:
                connector = _indent + _TREE_LAST
                child_prefix = _indent + _TREE_SPACE
            else:
                connector = _indent + _TREE_BRANCH
                child_prefix = _indent + _TREE_PIPE
            if isinstance(value, dict):
                lines.append(f"{connector}{key}:")
                self._render_dict(value, child_prefix, lines)
            elif isinstance(value, list):
                lines.append(f"{connector}{key}:")
                self._render_list(value, child_prefix, lines)
            else:
                val_lines = str(value).splitlines() or [""]
                lines.append(f"{connector}{key}: {val_lines[0]}")
                for vl in val_lines[1:]:
                    lines.append(f"{child_prefix}{vl}")
        return "\n".join(lines)


class ColorTreeFormat(TreeFormat):
    """
    Colored tree formatter for logging.

    """

    def __init__(self) -> None:
        super().__init__()
        self._colors = _COLOR_CONFIG
        self._reset = _COLOR_RESET

    def format(
        self,
        record: LogEvent,
    ) -> str:
        _payload: str = super().format(record)
        _color: str = self._colors.get(record.levelname, "")
        _reset: str = self._reset
        return f"{_color}{_payload}{_reset}"


class TextFormat(logging.Formatter):
    """
    Plain console formatter

    """

    def __init__(self) -> None:
        super().__init__()
        self._inner = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s]: %(message)s",
            datefmt=_READABLE_DATE_FORMAT,
        )

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        return self._inner.format(record)


class ColorTextFormat(TextFormat):
    """
    Colored console formatter

    """

    def __init__(self) -> None:
        super().__init__()
        self._colors = _COLOR_CONFIG
        self._reset = _COLOR_RESET

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        _payload: str = super().format(record)
        _color: str = self._colors.get(record.levelname, "")
        _reset: str = self._reset
        return f"{_color}{_payload}{_reset}"


# File formatters


class FileFormat(logging.Formatter):
    """
    File JSONlines formatter

    """

    def __init__(self) -> None:
        super().__init__()
        self._sort_keys = True
        self._ensure_ascii = False

    def format(
        self,
        record: LogEvent,
    ) -> str:
        return json.dumps(
            record.export(),
            indent=None,
            sort_keys=self._sort_keys,
            ensure_ascii=self._ensure_ascii,
        )


# Format factory for managing global formatters


class FormatFactory:
    def __init__(self) -> None:
        self._registry: dict[str, logging.Formatter] = {}
        self._default: logging.Formatter = TextFormat()

    def add(
        self,
        name: str,
        klass: logging.Formatter,
    ) -> None:
        _identifier = name.lower()
        self._registry[_identifier] = klass

    def get(
        self,
        name: str | None = None,
    ) -> logging.Formatter | None:
        _identifier = (name or "").lower()
        return self._registry.get(
            _identifier,
            self._default,
        )


GlbFormatFactory = FormatFactory()
GlbFormatFactory.add("text", TextFormat())
GlbFormatFactory.add("colortext", ColorTextFormat())
GlbFormatFactory.add("tree", TreeFormat())
GlbFormatFactory.add("colortree", ColorTreeFormat())
