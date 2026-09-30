from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.jitter.jitter import Jitter


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestJitterInit:
    def test_default_min_and_max_seconds(self):
        jitter = Jitter()
        assert jitter.min_seconds == 0.0
        assert jitter.max_seconds == 1.0

    def test_explicit_bounds_are_kept(self):
        jitter = Jitter(min_seconds=0.5, max_seconds=2.0)
        assert jitter.min_seconds == 0.5
        assert jitter.max_seconds == 2.0

    def test_negative_min_seconds_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Jitter(min_seconds=-0.1)

    def test_negative_max_seconds_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Jitter(max_seconds=-0.1)


class TestJitterRun:
    def test_sleeps_for_uniform_random_value_rounded_to_3_decimals(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.time.sleep", _sleep)
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.random.uniform", lambda a, b: 0.123456)
        Jitter(min_seconds=0.0, max_seconds=1.0).run()
        _sleep.assert_called_once_with(0.123)

    def test_uniform_is_called_with_min_and_max_bounds(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.time.sleep", MagicMock())
        _uniform = MagicMock(return_value=0.5)
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.random.uniform", _uniform)
        Jitter(min_seconds=0.2, max_seconds=0.8).run()
        _uniform.assert_called_once_with(0.2, 0.8)

    def test_zero_max_seconds_does_not_sleep(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.time.sleep", _sleep)
        Jitter(min_seconds=0.0, max_seconds=0.0).run()
        _sleep.assert_not_called()

    def test_logs_debug_message_with_rounded_interval(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.time.sleep", MagicMock())
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.random.uniform", lambda a, b: 0.123456)
        logstream = _mock_logstream()
        Jitter(min_seconds=0.0, max_seconds=1.0, logstream=logstream).run()
        logstream.debug.assert_called_once()
        assert "0.123s OK" in logstream.debug.call_args.kwargs["msg"]

    def test_zero_max_seconds_does_not_log(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.jitter.jitter.time.sleep", MagicMock())
        logstream = _mock_logstream()
        Jitter(min_seconds=0.0, max_seconds=0.0, logstream=logstream).run()
        logstream.debug.assert_not_called()
