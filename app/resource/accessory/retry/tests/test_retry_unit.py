from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.retry.retry import Retry, RetryResult

_SLEEP_PATH = "app.resource.accessory.retry.retry.time.sleep"


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


@pytest.fixture
def sleep(monkeypatch) -> MagicMock:
    _sleep = MagicMock()
    monkeypatch.setattr(_SLEEP_PATH, _sleep)
    return _sleep


class TestRetryInit:
    def test_defaults(self):
        retry = Retry()
        assert retry.max_retries == 1
        assert retry.interval == 5
        assert retry.backoff_rate == 1.0
        assert retry.raise_on_exception is True
        assert retry.critical_error_exprs == []
        assert retry.ignore_error_exprs == []

    def test_explicit_fields_are_kept(self):
        retry = Retry(
            max_retries=3,
            interval=2.0,
            backoff_rate=1.5,
            raise_on_exception=False,
            critical_error_exprs=["*fatal*"],
            ignore_error_exprs=["*timeout*"],
        )
        assert retry.max_retries == 3
        assert retry.interval == 2.0
        assert retry.backoff_rate == 1.5
        assert retry.raise_on_exception is False
        assert retry.critical_error_exprs == ["*fatal*"]
        assert retry.ignore_error_exprs == ["*timeout*"]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_retries": -1},
            {"interval": -1.0},
            {"backoff_rate": -1.0},
            {"interval": float("nan")},
            {"interval": float("inf")},
            {"backoff_rate": float("inf")},
        ],
    )
    def test_invalid_values_raise_validation_error(self, kwargs):
        with pytest.raises(ValidationError):
            Retry(**kwargs)


class TestRetryDelay:
    def test_delay_at_attempt_zero_equals_interval(self):
        retry = Retry(interval=5.0, backoff_rate=2.0)
        assert retry._delay() == 5.0

    def test_delay_grows_by_backoff_rate_each_attempt(self, sleep):
        retry = Retry(max_retries=5, interval=1.0, backoff_rate=2.0)
        retry.run()
        assert retry._delay() == 2.0
        retry.run()
        assert retry._delay() == 4.0

    def test_delay_is_rounded_to_3_decimals(self):
        retry = Retry(interval=1.0, backoff_rate=1.0 / 3)
        retry._attempt = 1
        assert retry._delay() == round(1.0 / 3, 3)


class TestRetryClassify:
    def test_none_error_returns_none(self):
        assert Retry()._classify_error(None) is None

    def test_no_pattern_match_returns_none(self):
        retry = Retry(critical_error_exprs=["*fatal*"], ignore_error_exprs=["*timeout*"])
        assert retry._classify_error("some other error") is None

    def test_ignore_pattern_match_returns_ignored(self):
        retry = Retry(ignore_error_exprs=["*timeout*"])
        assert retry._classify_error("connection timeout") == RetryResult.IGNORED

    def test_critical_pattern_match_returns_critical(self):
        retry = Retry(critical_error_exprs=["*fatal*"])
        assert retry._classify_error("fatal error") == RetryResult.CRITICAL

    def test_critical_takes_precedence_over_ignore(self):
        retry = Retry(critical_error_exprs=["*error*"], ignore_error_exprs=["*error*"])
        assert retry._classify_error("some error") == RetryResult.CRITICAL

    def test_exception_is_matched_by_its_text(self):
        retry = Retry(critical_error_exprs=["*boom*"])
        assert retry._classify_error(ValueError("boom happened")) == RetryResult.CRITICAL

    def test_match_is_case_sensitive(self):
        retry = Retry(critical_error_exprs=["*fatal*"])
        assert retry._classify_error("FATAL") is None


class TestRetryRun:
    def test_success_sleeps_for_delay_and_increments_attempt(self, sleep):
        retry = Retry(max_retries=3, interval=1.0, backoff_rate=1.0)
        assert retry.run() == RetryResult.SUCCESS
        sleep.assert_called_once_with(1.0)
        assert retry._attempt == 1

    def test_unmatched_error_still_retries(self, sleep):
        retry = Retry(max_retries=1, critical_error_exprs=["*fatal*"])
        assert retry.run(error="transient") == RetryResult.SUCCESS
        sleep.assert_called_once()

    def test_exhausted_raises_runtime_error_for_none_error(self, sleep):
        retry = Retry(max_retries=0)
        with pytest.raises(RuntimeError, match="retry exhausted"):
            retry.run()
        sleep.assert_not_called()

    def test_exhausted_includes_error_text_in_message(self, sleep):
        retry = Retry(max_retries=0)
        with pytest.raises(RuntimeError, match="retry exhausted after 0 attempts: oops"):
            retry.run(error="oops")

    def test_exhausted_reraises_original_exception(self, sleep):
        retry = Retry(max_retries=0)
        _err = ValueError("oops")
        with pytest.raises(ValueError) as exc_info:
            retry.run(error=_err)
        assert exc_info.value is _err

    def test_exhausted_after_consuming_all_retries(self, sleep):
        retry = Retry(max_retries=2)
        assert retry.run() == RetryResult.SUCCESS
        assert retry.run() == RetryResult.SUCCESS
        with pytest.raises(RuntimeError, match="retry exhausted after 2 attempts"):
            retry.run()
        assert sleep.call_count == 2

    def test_exhausted_returns_result_and_warns_when_not_raising(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(max_retries=0, raise_on_exception=False, logstream=logstream)
        assert retry.run() == RetryResult.EXHAUSTED
        sleep.assert_not_called()
        logstream.warning.assert_called_once()
        logstream.error.assert_not_called()

    def test_exhausted_raising_logs_error(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(max_retries=0, logstream=logstream)
        with pytest.raises(RuntimeError):
            retry.run()
        logstream.error.assert_called_once()

    def test_ignore_match_returns_without_sleep_or_attempt_increment(self, sleep):
        retry = Retry(ignore_error_exprs=["*timeout*"])
        assert retry.run(error="connection timeout") == RetryResult.IGNORED
        sleep.assert_not_called()
        assert retry._attempt == 0

    def test_ignore_match_wins_over_exhausted(self, sleep):
        retry = Retry(max_retries=0, ignore_error_exprs=["*timeout*"])
        assert retry.run(error="connection timeout") == RetryResult.IGNORED

    def test_critical_string_raises_runtime_error_without_sleep(self, sleep):
        retry = Retry(critical_error_exprs=["*fatal*"])
        with pytest.raises(RuntimeError, match="critical error matched.*fatal error"):
            retry.run(error="fatal error")
        sleep.assert_not_called()

    def test_critical_exception_reraises_same_instance(self, sleep):
        retry = Retry(critical_error_exprs=["*boom*"])
        _err = ValueError("boom happened")
        with pytest.raises(ValueError) as exc_info:
            retry.run(error=_err)
        assert exc_info.value is _err

    def test_critical_returns_result_when_not_raising(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(
            critical_error_exprs=["*fatal*"],
            raise_on_exception=False,
            logstream=logstream,
        )
        assert retry.run(error="fatal error") == RetryResult.CRITICAL
        sleep.assert_not_called()
        logstream.warning.assert_called_once()

    def test_critical_wins_over_exhausted(self, sleep):
        retry = Retry(max_retries=0, critical_error_exprs=["*fatal*"], raise_on_exception=False)
        assert retry.run(error="fatal error") == RetryResult.CRITICAL

    def test_logs_debug_message_with_attempt_and_delay(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(interval=2.0, backoff_rate=1.0, logstream=logstream)
        retry.run()
        logstream.debug.assert_called_once()
        assert "attempt=1 delay=2.0s OK" in logstream.debug.call_args.kwargs["msg"]

    def test_zero_interval_sleeps_zero_seconds(self, sleep):
        retry = Retry(max_retries=1, interval=0)
        retry.run()
        sleep.assert_called_once_with(0.0)


class TestRetryReset:
    def test_reset_sets_attempt_back_to_zero(self, sleep):
        retry = Retry(max_retries=5)
        retry.run()
        assert retry._attempt == 1
        retry.reset()
        assert retry._attempt == 0

    def test_reset_restores_retry_budget(self, sleep):
        retry = Retry(max_retries=1)
        retry.run()
        retry.reset()
        assert retry.run() == RetryResult.SUCCESS

    def test_reset_logs_debug_message(self):
        logstream = _mock_logstream()
        retry = Retry(logstream=logstream)
        retry.reset()
        logstream.debug.assert_called_once()
        assert "reset OK" in logstream.debug.call_args.kwargs["msg"]
