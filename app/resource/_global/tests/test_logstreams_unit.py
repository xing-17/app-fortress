from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from app.internal.logstream import LogStream
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.setting import GlobalSetting
from app.setting._log import LogSetting


def _log_setting(name: str, **overrides) -> LogSetting:
    return LogSetting(name=name, console_verbose=False, **overrides)


def _patch_system(monkeypatch, log_setting: LogSetting) -> SimpleNamespace:
    _setting = SimpleNamespace(log=log_setting)
    monkeypatch.setattr(GlobalSetting, "get_system", classmethod(lambda cls: _setting))
    return _setting


class TestGlobalLogStreamsLoad:
    def test_load_builds_default_stream_from_system_setting(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("sys"))
        GlobalLogStreams.load()
        assert set(GlobalLogStreams.streams) == {"sys"}
        assert isinstance(GlobalLogStreams.streams["sys"], LogStream)
        assert GlobalLogStreams.default is GlobalLogStreams.streams["sys"]

    def test_load_wraps_stream_creation_errors_in_value_error(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("broken"))

        def _raise(cls, setting):
            raise RuntimeError("boom")

        monkeypatch.setattr(LogStream, "from_setting", classmethod(_raise))
        with pytest.raises(ValueError, match="Failed to load log stream"):
            GlobalLogStreams.load()


class TestGlobalLogStreamsEnsureLoaded:
    def test_get_default_lazy_loads_when_not_loaded(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("lazy"))
        result = GlobalLogStreams.get_default()
        assert isinstance(result, LogStream)
        assert result.name == "lazy"

    def test_get_default_does_not_reload_when_already_cached(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("cached"))
        GlobalLogStreams.load()

        def _fail_load(cls):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalLogStreams, "load", classmethod(_fail_load))
        result = GlobalLogStreams.get_default()
        assert result.name == "cached"


class TestGlobalLogStreamsGetDefault:
    def test_get_default_stays_on_system_stream_after_adding_more_streams(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        GlobalLogStreams.add_stream(_log_setting("secondary"))
        assert GlobalLogStreams.get_default().name == "primary"


class TestGlobalLogStreamsAddStream:
    def test_add_stream_adds_new_entry(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        result = GlobalLogStreams.add_stream(_log_setting("Secondary"))
        assert isinstance(result, LogStream)
        assert set(GlobalLogStreams.list_stream_names()) == {"primary", "secondary"}

    def test_add_stream_raises_value_error_on_duplicate_name(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        with pytest.raises(ValueError, match="Duplicate log stream entry"):
            GlobalLogStreams.add_stream(_log_setting("PRIMARY"))

    def test_add_stream_wraps_factory_errors_in_value_error(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()

        _original_from_setting = LogStream.from_setting

        def _maybe_raise(cls, setting):
            if setting.name == "broken":
                raise RuntimeError("boom")
            return _original_from_setting(setting)

        monkeypatch.setattr(LogStream, "from_setting", classmethod(_maybe_raise))
        with pytest.raises(ValueError, match="Failed to add log stream 'broken'"):
            GlobalLogStreams.add_stream(_log_setting("broken"))


class TestGlobalLogStreamsGetStream:
    def test_get_stream_returns_none_for_missing_when_not_strict(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        assert GlobalLogStreams.get_stream("missing") is None

    def test_get_stream_raises_value_error_for_missing_when_strict(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        with pytest.raises(ValueError, match="not found"):
            GlobalLogStreams.get_stream("missing", strict=True)

    def test_get_stream_is_case_insensitive(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("Primary"))
        GlobalLogStreams.load()
        result = GlobalLogStreams.get_stream("PRIMARY")
        assert result is not None
        assert result.name == "primary"


class TestGlobalLogStreamsListStreams:
    def test_list_stream_names_returns_all_names(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        GlobalLogStreams.add_stream(_log_setting("secondary"))
        assert set(GlobalLogStreams.list_stream_names()) == {"primary", "secondary"}

    def test_list_streams_returns_all_instances(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        GlobalLogStreams.add_stream(_log_setting("secondary"))
        result = GlobalLogStreams.list_streams()
        assert {s.name for s in result} == {"primary", "secondary"}

    def test_list_streams_returns_independent_snapshot(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        result = GlobalLogStreams.list_streams()
        result.append(LogStream(name="mutated", console_verbose=False))
        assert len(GlobalLogStreams.streams) == 1


class TestGlobalLogStreamsReset:
    def test_reset_clears_cached_streams_and_default(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("primary"))
        GlobalLogStreams.load()
        assert GlobalLogStreams.streams is not None
        GlobalLogStreams.reset()
        assert GlobalLogStreams.streams is None
        assert GlobalLogStreams.default is None


class TestGlobalLogStreamsConcurrency:
    def test_get_default_under_concurrent_access_loads_only_once(self, monkeypatch):
        _patch_system(monkeypatch, _log_setting("threaded"))

        _original_from_setting = LogStream.from_setting
        _call_count = {"n": 0}

        def _counting_from_setting(cls, setting):
            _call_count["n"] += 1
            return _original_from_setting(setting)

        monkeypatch.setattr(LogStream, "from_setting", classmethod(_counting_from_setting))

        _results: list[LogStream | None] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalLogStreams.get_default())

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
