from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.coolant.coolant import Coolant


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestCoolantInit:
    def test_default_interval_is_zero(self):
        coolant = Coolant()
        assert coolant.interval == 0.0

    def test_explicit_interval_is_kept(self):
        coolant = Coolant(interval=1.5)
        assert coolant.interval == 1.5

    def test_negative_interval_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Coolant(interval=-0.1)


class TestCoolantRun:
    def test_zero_interval_does_not_sleep(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.coolant.coolant.time.sleep", _sleep)
        Coolant(interval=0.0).run()
        _sleep.assert_not_called()

    def test_positive_interval_sleeps_for_interval(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.coolant.coolant.time.sleep", _sleep)
        Coolant(interval=0.25).run()
        _sleep.assert_called_once_with(0.25)

    def test_zero_interval_does_not_log(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.coolant.coolant.time.sleep", MagicMock())
        logstream = _mock_logstream()
        Coolant(interval=0.0, logstream=logstream).run()
        logstream.debug.assert_not_called()

    def test_positive_interval_logs_debug_message(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.coolant.coolant.time.sleep", MagicMock())
        logstream = _mock_logstream()
        Coolant(interval=0.25, logstream=logstream).run()
        logstream.debug.assert_called_once()
        assert "0.25s OK" in logstream.debug.call_args.kwargs["msg"]
