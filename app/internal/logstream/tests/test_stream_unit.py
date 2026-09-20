from __future__ import annotations

import logging

import pytest

from app.internal.logstream.group import ConsoleGroup, FileGroup
from app.internal.logstream.stream import LogStream
from app.internal.util.timezone import ITimezone
from app.setting._log import LogSetting


class _RecordCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _make_stream(**overrides) -> LogStream:
    kwargs = dict(console_verbose=False)
    kwargs.update(overrides)
    return LogStream(**kwargs)


def _collect(stream: LogStream) -> _RecordCollector:
    collector = _RecordCollector()
    stream.addHandler(collector)
    return collector


class TestLogStreamFromSetting:
    def test_maps_setting_fields_onto_stream(self, tmp_path):
        setting = LogSetting(
            name="svc",
            level="DEBUG",
            timezone="UTC",
            metadata={"app": "x"},
            tags={"env": "prod"},
            console_verbose=False,
            console_format="TEXT",
            file_path=str(tmp_path),
            file_max_items=10,
        )
        stream = LogStream.from_setting(setting)
        assert stream.name == "svc"
        assert stream.level == logging.DEBUG
        assert stream._timezone == ITimezone.resolve("UTC")
        assert stream._metadata == {"app": "x"}
        assert stream._tags == setting.tags
        assert stream._console_format == "TEXT"
        assert stream._file_max_items == 10
        assert isinstance(stream._file, FileGroup)

    def test_uses_setting_defaults_when_not_customized(self):
        stream = LogStream.from_setting(LogSetting())
        assert stream.name == "default"
        assert stream.level == logging.INFO
        assert isinstance(stream._console, ConsoleGroup)

    def test_respects_console_verbose_false(self):
        stream = LogStream.from_setting(LogSetting(console_verbose=False))
        assert stream._console is None


class TestLogStreamResolveName:
    def test_defaults_to_default_name_when_none(self):
        stream = _make_stream()
        assert stream.name == "default"

    def test_lowercases_provided_name(self):
        stream = _make_stream(name="APP")
        assert stream.name == "app"


class TestLogStreamResolveLevel:
    def test_defaults_to_info_when_none(self):
        stream = _make_stream()
        assert stream.level == logging.INFO

    def test_accepts_case_insensitive_level_name(self):
        stream = _make_stream(level="debug")
        assert stream.level == logging.DEBUG

    def test_falls_back_to_info_for_unknown_level(self):
        stream = _make_stream(level="not-a-level")
        assert stream.level == logging.INFO


class TestLogStreamConsoleHandler:
    def test_adds_console_handler_when_verbose(self):
        stream = LogStream(console_verbose=True)
        assert isinstance(stream._console, ConsoleGroup)
        assert stream._console in stream.handlers

    def test_no_console_handler_when_not_verbose(self):
        stream = _make_stream()
        assert stream._console is None
        assert stream.handlers == []

    def test_default_console_writes_to_stdout(self, capsys):
        stream = LogStream()
        stream.info("hello")
        assert "hello" in capsys.readouterr().out


class TestLogStreamFileHandler:
    def test_no_file_handler_when_path_is_none(self):
        stream = _make_stream(file_path=None)
        assert stream._file is None

    def test_adds_file_handler_when_path_given(self, tmp_path):
        stream = _make_stream(file_path=tmp_path, name="app")
        assert isinstance(stream._file, FileGroup)
        assert stream._file in stream.handlers


class TestLogStreamRead:
    def test_returns_empty_list_without_file_handler(self):
        stream = _make_stream()
        assert stream.read() == []

    def test_reads_from_file_handler(self, tmp_path):
        stream = _make_stream(file_path=tmp_path, name="app")
        stream.info("hello")
        result = stream.read()
        assert len(result) == 1
        assert result[0]["msg"] == "hello"


class TestLogStreamEventContext:
    def test_info_merges_instance_and_call_metadata(self):
        stream = _make_stream(metadata={"app": "svc"})
        collector = _collect(stream)
        stream.info("hello", metadata={"user_id": 1})
        assert collector.records[0].metadata == {"app": "svc", "user_id": 1}

    def test_info_merges_instance_and_call_tags(self):
        stream = _make_stream(tags={"env": "prod"})
        collector = _collect(stream)
        stream.info("hello", tags={"module": "core"})
        assert collector.records[0].tags == {"env": "prod", "module": "core"}

    def test_info_sets_metrics_without_instance_default(self):
        stream = _make_stream()
        collector = _collect(stream)
        stream.info("hello", metrics={"duration_ms": 42})
        assert collector.records[0].metrics == {"duration_ms": 42}

    def test_call_metadata_overrides_instance_metadata(self):
        stream = _make_stream(metadata={"app": "svc", "env": "dev"})
        collector = _collect(stream)
        stream.info("hello", metadata={"env": "prod"})
        assert collector.records[0].metadata == {"app": "svc", "env": "prod"}

    def test_no_metadata_call_falls_back_to_instance_metadata(self):
        stream = _make_stream(metadata={"app": "svc"})
        collector = _collect(stream)
        stream.info("hello")
        assert collector.records[0].metadata == {"app": "svc"}

    @pytest.mark.parametrize(
        "method,level",
        [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_level_methods_forward_metadata(self, method, level):
        stream = _make_stream(level="debug")
        collector = _collect(stream)
        getattr(stream, method)("hello", metadata={"k": "v"})
        record = collector.records[0]
        assert record.levelno == level
        assert record.metadata == {"k": "v"}

    def test_log_forwards_metadata(self):
        stream = _make_stream(level="debug")
        collector = _collect(stream)
        stream.log(logging.WARNING, "hello", metadata={"k": "v"})
        record = collector.records[0]
        assert record.levelno == logging.WARNING
        assert record.metadata == {"k": "v"}

    def test_exception_captures_exc_info(self):
        stream = _make_stream()
        collector = _collect(stream)
        try:
            raise ValueError("boom")
        except ValueError:
            stream.exception("failed")
        assert collector.records[0].exc_info[0] is ValueError


class TestLogStreamMakeRecord:
    def test_extra_keys_without_conflict_are_attached_to_record(self):
        stream = _make_stream()
        collector = _collect(stream)
        stream.info("hello", extra={"request_id": "abc"})
        assert collector.records[0].request_id == "abc"

    def test_raises_when_extra_key_conflicts_with_reserved_logrecord_field(self):
        stream = _make_stream()
        _collect(stream)
        with pytest.raises(KeyError):
            stream.info("hello", extra={"lineno": 999})

    def test_raises_when_extra_key_conflicts_with_logevent_field(self):
        stream = _make_stream()
        _collect(stream)
        with pytest.raises(KeyError):
            stream.info("hello", extra={"created_at": "boom"})
