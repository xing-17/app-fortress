from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.internal.logstream.event import LogEvent
from app.internal.logstream.format import (
    ColorTextFormat,
    ColorTreeFormat,
    FileFormat,
    GlbFormatFactory,
    TextFormat,
    TreeFormat,
)


def _make_event(**overrides) -> LogEvent:
    kwargs = dict(
        name="test",
        level=logging.INFO,
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
        pathname="/path/to/module.py",
        lineno=42,
        msg="hello %s",
        args=("world",),
    )
    kwargs.update(overrides)
    return LogEvent(**kwargs)


class TestTextFormat:
    def test_format_includes_level_and_message(self):
        result = TextFormat().format(_make_event())
        assert "[INFO]" in result
        assert "hello world" in result


class TestColorTextFormat:
    def test_format_wraps_output_in_level_color(self):
        result = ColorTextFormat().format(_make_event(level=logging.ERROR))
        assert result.startswith("\x1b[31m")
        assert result.endswith("\x1b[0m")
        assert "hello world" in result


class TestTreeFormat:
    def test_format_header_line(self):
        result = TreeFormat().format(_make_event())
        assert "[INFO]: hello world" in result.splitlines()[0]

    def test_format_renders_nested_metadata(self):
        event = _make_event(metadata={"user": {"id": 123}})
        result = TreeFormat().format(event)
        assert "metadata:" in result
        assert "user:" in result
        assert "id: 123" in result

    def test_format_omits_empty_fields(self):
        result = TreeFormat().format(_make_event())
        assert "metadata" not in result
        assert "metrics" not in result
        assert "tags" not in result


class TestColorTreeFormat:
    def test_format_wraps_output_in_level_color(self):
        result = ColorTreeFormat().format(_make_event(level=logging.WARNING))
        assert result.startswith("\x1b[38;5;208m")
        assert result.endswith("\x1b[0m")


class TestFileFormat:
    def test_format_produces_valid_json_line(self):
        event = _make_event(tags={"module": "core"})
        parsed = json.loads(FileFormat().format(event))
        assert parsed["msg"] == "hello world"
        assert parsed["tags"] == {"module": "core"}

    def test_format_preserves_non_ascii_characters(self):
        result = FileFormat().format(_make_event(msg="你好", args=()))
        assert "你好" in result


class TestFormatFactory:
    def test_get_known_names_are_case_insensitive(self):
        assert isinstance(GlbFormatFactory.get("TEXT"), TextFormat)
        assert isinstance(GlbFormatFactory.get("tree"), TreeFormat)

    def test_get_unknown_name_returns_default(self):
        assert isinstance(GlbFormatFactory.get("does-not-exist"), TextFormat)

    def test_get_none_returns_default(self):
        assert isinstance(GlbFormatFactory.get(None), TextFormat)
