from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.backoff.backoff import Backoff


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestBackoffInit:
    def test_default_values(self):
        backoff = Backoff()
        assert backoff.interval == 5
        assert backoff.rate == 1.0
        assert backoff.max_retries == 3
        assert backoff.raise_on_max_retries is True

    def test_explicit_values_are_kept(self):
        backoff = Backoff(interval=1.0, rate=2.0, max_retries=5, raise_on_max_retries=False)
        assert backoff.interval == 1.0
        assert backoff.rate == 2.0
        assert backoff.max_retries == 5
        assert backoff.raise_on_max_retries is False

    def test_negative_interval_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Backoff(interval=-0.1)

    def test_negative_rate_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Backoff(rate=-0.1)

    def test_negative_max_retries_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Backoff(max_retries=-1)


class TestBackoffDelay:
    def test_delay_at_attempt_zero_equals_interval(self):
        backoff = Backoff(interval=2.0, rate=2.0, max_retries=10)
        assert backoff._delay() == 2.0

    def test_delay_grows_by_rate_per_attempt(self):
        backoff = Backoff(interval=1.0, rate=2.0, max_retries=10)
        backoff._add_attempt()
        assert backoff._delay() == 2.0
        backoff._add_attempt()
        assert backoff._delay() == 4.0

    def test_delay_is_rounded_to_3_decimals(self):
        backoff = Backoff(interval=1.0, rate=1.0 / 3, max_retries=10)
        backoff._add_attempt()
        assert backoff._delay() == round(1.0 / 3, 3)


class TestBackoffRun:
    def test_first_run_sleeps_for_base_interval(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", _sleep)
        Backoff(interval=0.5, max_retries=10).run()
        _sleep.assert_called_once_with(0.5)

    def test_run_increments_attempt(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", MagicMock())
        backoff = Backoff(interval=0.1, max_retries=10)
        backoff.run()
        assert backoff._attempt == 1
        backoff.run()
        assert backoff._attempt == 2

    def test_delay_grows_across_successive_runs(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", _sleep)
        backoff = Backoff(interval=1.0, rate=2.0, max_retries=10)
        backoff.run()
        backoff.run()
        backoff.run()
        assert [_call.args[0] for _call in _sleep.call_args_list] == [1.0, 2.0, 4.0]

    def test_logs_debug_message_with_attempt_and_seconds(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", MagicMock())
        logstream = _mock_logstream()
        Backoff(interval=0.5, max_retries=10, logstream=logstream).run()
        logstream.debug.assert_called_once()
        assert "attempt=1" in logstream.debug.call_args.kwargs["msg"]
        assert "0.5s OK" in logstream.debug.call_args.kwargs["msg"]

    def test_zero_max_retries_raises_immediately_without_sleep(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", _sleep)
        with pytest.raises(RuntimeError):
            Backoff(max_retries=0, raise_on_max_retries=True).run()
        _sleep.assert_not_called()

    def test_raises_runtime_error_once_max_retries_reached(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", MagicMock())
        backoff = Backoff(interval=0.1, max_retries=2, raise_on_max_retries=True)
        backoff.run()
        backoff.run()
        with pytest.raises(RuntimeError, match="backoff exhausted after 2 attempts"):
            backoff.run()

    def test_logs_error_when_raising_on_max_retries(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", MagicMock())
        logstream = _mock_logstream()
        backoff = Backoff(interval=0.1, max_retries=1, raise_on_max_retries=True, logstream=logstream)
        backoff.run()
        with pytest.raises(RuntimeError):
            backoff.run()
        logstream.error.assert_called_once()

    def test_warns_instead_of_raising_when_disabled(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", _sleep)
        logstream = _mock_logstream()
        backoff = Backoff(interval=0.1, max_retries=1, raise_on_max_retries=False, logstream=logstream)
        backoff.run()
        _sleep.reset_mock()
        backoff.run()
        _sleep.assert_not_called()
        logstream.warning.assert_called_once()

    def test_attempt_does_not_advance_past_max_retries_once_exhausted(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.backoff.backoff.time.sleep", MagicMock())
        backoff = Backoff(interval=0.1, max_retries=1, raise_on_max_retries=False)
        backoff.run()
        backoff.run()
        backoff.run()
        assert backoff._attempt == 1
