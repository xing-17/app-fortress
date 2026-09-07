from __future__ import annotations

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from app.internal.logstream.event import LogEvent


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


class TestLogEventConstruction:
    def test_defaults_to_empty_dicts_when_none(self):
        event = _make_event()
        assert event.metadata == {}
        assert event.metrics == {}
        assert event.tags == {}

    def test_stores_provided_metadata_metrics_tags(self):
        event = _make_event(
            metadata={"user_id": 123},
            metrics={"duration_ms": 42},
            tags={"module": "core"},
        )
        assert event.metadata == {"user_id": 123}
        assert event.metrics == {"duration_ms": 42}
        assert event.tags == {"module": "core"}


class TestLogEventExport:
    def test_export_basic_fields(self):
        result = _make_event().export()
        assert result["level"] == "INFO"
        assert result["created_at"] == "2024-06-01T12:00:00+0000"
        assert result["msg"] == "hello world"
        assert result["exc_info"] is None
        assert result["metadata"] == {}
        assert result["metrics"] == {}
        assert result["tags"] == {}

    def test_export_includes_metadata_metrics_tags(self):
        event = _make_event(
            metadata={"user_id": 123},
            metrics={"duration_ms": 42},
            tags={"module": "core"},
        )
        result = event.export()
        assert result["metadata"] == {"user_id": 123}
        assert result["metrics"] == {"duration_ms": 42}
        assert result["tags"] == {"module": "core"}

    def test_export_captures_exception_info(self):
        try:
            raise ValueError("boom")
        except ValueError:
            event = _make_event(exc_info=sys.exc_info())
        result = event.export()
        assert result["exc_info"] == {"type": "ValueError", "value": "boom"}
