from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.internal.logstream.event import LogEvent
from app.internal.logstream.format import FileFormat, GlbFormatFactory
from app.internal.logstream.group import ConsoleGroup, FileGroup


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


class TestConsoleGroup:
    def test_init_writes_to_stdout(self):
        handler = ConsoleGroup()
        assert handler.stream is sys.stdout

    def test_init_resolves_formatter_from_factory(self):
        handler = ConsoleGroup(format="tree")
        assert handler.formatter is GlbFormatFactory.get("tree")


class TestFileGroupResolveName:
    def test_defaults_to_default_name_when_none(self, tmp_path):
        group = FileGroup(path=tmp_path)
        assert group._name == "default"

    def test_lowercases_provided_name(self, tmp_path):
        group = FileGroup(path=tmp_path, name="APP")
        assert group._name == "app"


class TestFileGroupResolvePath:
    def test_directory_path_appends_name_log(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        assert group._path == (tmp_path / "app.log").resolve()

    def test_nested_missing_directory_is_created(self, tmp_path):
        target = tmp_path / "nested" / "app"
        group = FileGroup(path=target, name="fallback")
        assert group._path == (target / "fallback.log").resolve()

    def test_raises_when_path_is_an_existing_file(self, tmp_path):
        target = tmp_path / "custom.log"
        target.write_text("", encoding="utf-8")
        with pytest.raises(ValueError):
            FileGroup(path=target)

    def test_creates_missing_directory(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        FileGroup(path=target)
        assert target.is_dir()

    def test_expands_user_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        group = FileGroup(path="~/logs", name="app")
        assert group._path == (tmp_path / "logs" / "app.log").resolve()


class TestFileGroupResolveMaxItems:
    def test_defaults_when_none(self, tmp_path):
        group = FileGroup(path=tmp_path)
        assert group._max_items == FileGroup.default_max_items

    def test_accepts_positive_value(self, tmp_path):
        group = FileGroup(path=tmp_path, max_items=50)
        assert group._max_items == 50

    def test_raises_for_zero(self, tmp_path):
        with pytest.raises(ValueError):
            FileGroup(path=tmp_path, max_items=0)

    def test_raises_for_negative(self, tmp_path):
        with pytest.raises(ValueError):
            FileGroup(path=tmp_path, max_items=-1)


class TestFileGroupInit:
    def test_threshold_is_110_percent_of_max_items(self, tmp_path):
        group = FileGroup(path=tmp_path, max_items=10)
        assert group._threshold == 11

    def test_sets_file_formatter(self, tmp_path):
        group = FileGroup(path=tmp_path)
        assert isinstance(group.formatter, FileFormat)


class TestFileGroupCount:
    def test_zero_when_file_does_not_exist(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        assert group._n_lines == 0

    def test_counts_existing_lines_on_init(self, tmp_path):
        (tmp_path / "app.log").write_text("line1\nline2\nline3\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._n_lines == 3


class TestFileGroupTail:
    def test_returns_empty_list_when_file_missing(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail() == []

    def test_returns_all_lines_when_limit_is_none(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\nc\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail() == ["a\n", "b\n", "c\n"]

    def test_returns_last_n_lines_when_limit_given(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\nc\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail(limit=2) == ["b\n", "c\n"]

    def test_returns_empty_list_when_limit_is_zero(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail(limit=0) == []

    def test_returns_empty_list_when_limit_is_negative(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail(limit=-1) == []

    def test_limit_larger_than_available_lines_returns_all(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")
        assert group._tail(limit=100) == ["a\n", "b\n"]


class TestFileGroupEmit:
    def test_appends_formatted_line_to_file(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        group.emit(_make_event())
        lines = group._path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["msg"] == "hello world"

    def test_appends_multiple_events_in_order(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        group.emit(_make_event(msg="first", args=()))
        group.emit(_make_event(msg="second", args=()))
        lines = group._path.read_text(encoding="utf-8").splitlines()
        assert json.loads(lines[0])["msg"] == "first"
        assert json.loads(lines[1])["msg"] == "second"

    def test_increments_n_lines(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        group.emit(_make_event())
        assert group._n_lines == 1
        group.emit(_make_event())
        assert group._n_lines == 2

    def test_triggers_compaction_once_threshold_is_reached(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app", max_items=2)
        group.emit(_make_event(msg="one", args=()))
        group.emit(_make_event(msg="two", args=()))
        group.emit(_make_event(msg="three", args=()))
        lines = group._path.read_text(encoding="utf-8").splitlines()
        assert [json.loads(line)["msg"] for line in lines] == ["two", "three"]
        assert group._n_lines == 2

    def test_handles_format_errors_without_raising(self, tmp_path, monkeypatch):
        group = FileGroup(path=tmp_path, name="app")

        def _raise(event):
            raise RuntimeError("boom")

        handled = []
        monkeypatch.setattr(group, "format", _raise)
        monkeypatch.setattr(group, "handleError", lambda event: handled.append(event))

        event = _make_event()
        group.emit(event)

        assert handled == [event]
        assert not group._path.exists()


class TestFileGroupCompact:
    def test_keeps_only_last_max_items_lines(self, tmp_path):
        log_file = tmp_path / "app.log"
        log_file.write_text("a\nb\nc\nd\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app", max_items=2)

        group._compact()

        assert log_file.read_text(encoding="utf-8") == "c\nd\n"
        assert group._n_lines == 2

    def test_removes_temp_file_after_replace(self, tmp_path):
        (tmp_path / "app.log").write_text("a\nb\nc\n", encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app", max_items=2)

        group._compact()

        assert not (tmp_path / "app.log.tmp").exists()


class TestFileGroupRead:
    def test_returns_empty_list_when_file_missing(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        assert group.read() == []

    def test_returns_events_newest_first(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        group.emit(_make_event(msg="first", args=()))
        group.emit(_make_event(msg="second", args=()))

        result = group.read()

        assert [item["msg"] for item in result] == ["second", "first"]

    def test_skips_malformed_lines(self, tmp_path):
        (tmp_path / "app.log").write_text('not-json\n{"msg": "ok"}\n', encoding="utf-8")
        group = FileGroup(path=tmp_path, name="app")

        assert group.read() == [{"msg": "ok"}]

    def test_respects_limit(self, tmp_path):
        group = FileGroup(path=tmp_path, name="app")
        for i in range(5):
            group.emit(_make_event(msg=f"msg-{i}", args=()))

        result = group.read(limit=2)

        assert [item["msg"] for item in result] == ["msg-4", "msg-3"]
