from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.retry.retry import Retry


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestRetryInit:
    def test_defaults(self):
        retry = Retry()
        assert retry.max_retries == 1
        assert retry.interval == 5
        assert retry.backoff_rate == 1.0
        assert retry.raise_on_exhausted is True
        assert retry.critical_error_exprs == []
        assert retry.ignore_error_exprs == []

    def test_explicit_fields_are_kept(self):
        retry = Retry(
            max_retries=3,
            interval=2.0,
            backoff_rate=1.5,
            raise_on_exhausted=False,
            critical_error_exprs=["*fatal*"],
            ignore_error_exprs=["*timeout*"],
        )
        assert retry.max_retries == 3
        assert retry.interval == 2.0
        assert retry.backoff_rate == 1.5
        assert retry.raise_on_exhausted is False
        assert retry.critical_error_exprs == ["*fatal*"]
        assert retry.ignore_error_exprs == ["*timeout*"]

    def test_negative_max_retries_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Retry(max_retries=-1)

    def test_negative_interval_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Retry(interval=-1.0)

    def test_negative_backoff_rate_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Retry(backoff_rate=-1.0)


class TestRetryDelay:
    def test_delay_at_attempt_zero_equals_interval(self):
        retry = Retry(interval=5.0, backoff_rate=2.0)
        assert retry._delay() == 5.0

    def test_delay_grows_by_backoff_rate_each_attempt(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", MagicMock())
        retry = Retry(max_retries=5, interval=1.0, backoff_rate=2.0)
        retry.run()
        assert retry._delay() == 2.0
        retry.run()
        assert retry._delay() == 4.0

    def test_delay_is_rounded_to_3_decimals(self):
        retry = Retry(interval=1.0, backoff_rate=1.0 / 3)
        retry._attempt = 1
        assert retry._delay() == round(1.0 * (1.0 / 3), 3)


class TestRetryShouldRetry:
    def test_none_error_returns_true(self):
        retry = Retry()
        assert retry._should_retry(None) is True

    def test_no_pattern_match_returns_true(self):
        retry = Retry(critical_error_exprs=["*fatal*"], ignore_error_exprs=["*timeout*"])
        assert retry._should_retry("some other error") is True

    def test_ignore_pattern_match_returns_false(self):
        retry = Retry(ignore_error_exprs=["*timeout*"])
        assert retry._should_retry("connection timeout") is False

    def test_critical_pattern_match_with_string_raises_runtime_error(self):
        retry = Retry(critical_error_exprs=["*fatal*"])
        with pytest.raises(RuntimeError, match="fatal error"):
            retry._should_retry("fatal error")

    def test_critical_pattern_match_with_exception_reraises_same_instance(self):
        retry = Retry(critical_error_exprs=["*boom*"])
        _err = ValueError("boom happened")
        with pytest.raises(ValueError) as exc_info:
            retry._should_retry(_err)
        assert exc_info.value is _err

    def test_critical_takes_precedence_over_ignore_when_both_match(self):
        retry = Retry(critical_error_exprs=["*error*"], ignore_error_exprs=["*error*"])
        with pytest.raises(RuntimeError):
            retry._should_retry("some error")


class TestRetryRun:
    def test_sleeps_for_delay_and_increments_attempt(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", _sleep)
        retry = Retry(max_retries=3, interval=1.0, backoff_rate=1.0)
        retry.run()
        _sleep.assert_called_once_with(1.0)
        assert retry._attempt == 1

    def test_exhausted_raises_runtime_error_when_raise_on_exhausted_true(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", MagicMock())
        retry = Retry(max_retries=0, raise_on_exhausted=True)
        with pytest.raises(RuntimeError, match="retry exhausted"):
            retry.run()

    def test_exhausted_logs_warning_and_returns_when_raise_on_exhausted_false(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", _sleep)
        logstream = _mock_logstream()
        retry = Retry(max_retries=0, raise_on_exhausted=False, logstream=logstream)
        retry.run()
        _sleep.assert_not_called()
        logstream.warning.assert_called_once()

    def test_ignore_match_returns_without_sleep_or_attempt_increment(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", _sleep)
        retry = Retry(ignore_error_exprs=["*timeout*"])
        retry.run(error="connection timeout")
        _sleep.assert_not_called()
        assert retry._attempt == 0

    def test_critical_match_raises_immediately_without_sleep(self, monkeypatch):
        _sleep = MagicMock()
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", _sleep)
        retry = Retry(critical_error_exprs=["*fatal*"])
        with pytest.raises(RuntimeError, match="fatal error"):
            retry.run(error="fatal error")
        _sleep.assert_not_called()

    def test_logs_debug_message_with_attempt_and_seconds(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", MagicMock())
        logstream = _mock_logstream()
        retry = Retry(interval=2.0, backoff_rate=1.0, logstream=logstream)
        retry.run()
        logstream.debug.assert_called_once()
        assert "attempt=1 2.0s OK" in logstream.debug.call_args.kwargs["msg"]


class TestRetryReset:
    def test_reset_sets_attempt_back_to_zero(self, monkeypatch):
        monkeypatch.setattr("app.resource.accessory.retry.retry.time.sleep", MagicMock())
        retry = Retry(max_retries=5)
        retry.run()
        assert retry._attempt == 1
        retry.reset()
        assert retry._attempt == 0

    def test_reset_logs_debug_message(self):
        logstream = _mock_logstream()
        retry = Retry(logstream=logstream)
        retry.reset()
        logstream.debug.assert_called_once()
        assert "reset OK" in logstream.debug.call_args.kwargs["msg"]
