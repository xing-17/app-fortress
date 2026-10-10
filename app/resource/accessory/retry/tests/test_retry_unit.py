from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.retry.retry import Attempt, Retry, RetryAction

_SLEEP_PATH = "app.resource.accessory.retry.retry.time.sleep"


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


@pytest.fixture
def sleep(monkeypatch) -> MagicMock:
    _sleep = MagicMock()
    monkeypatch.setattr(_SLEEP_PATH, _sleep)
    return _sleep


class _Flaky:
    """Callable that raises `errors` one per call, then returns `value`."""

    def __init__(self, errors: list[BaseException], value: str = "ok") -> None:
        self.errors = list(errors)
        self.value = value
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return self.value


def _drive(retry: Retry, fn) -> str | None:
    result = None
    for attempt in retry.attempts():
        with attempt:
            result = fn()
    return result


def _sleeps(sleep: MagicMock) -> list[float]:
    return [c.args[0] for c in sleep.call_args_list]


class TestRetryAction:
    def test_members_and_values(self):
        assert {m.name: m.value for m in RetryAction} == {
            "ABORT": "ABORT",
            "SKIP": "SKIP",
            "GIVE_UP": "GIVE_UP",
            "RETRY": "RETRY",
        }

    def test_members_compare_equal_to_plain_strings(self):
        assert RetryAction.RETRY == "RETRY"


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

    def test_pattern_lists_are_not_shared_between_instances(self):
        _a, _b = Retry(), Retry()
        _a.critical_error_exprs.append("*x*")
        _a.ignore_error_exprs.append("*y*")
        assert _b.critical_error_exprs == []
        assert _b.ignore_error_exprs == []


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

    def test_zero_backoff_rate_delays_only_first_attempt(self):
        retry = Retry(interval=3.0, backoff_rate=0.0)
        assert retry._delay() == 3.0
        retry._attempt = 1
        assert retry._delay() == 0.0


class TestRetryClassify:
    def test_none_error_returns_none(self):
        assert Retry()._classify_error(None) is None

    def test_no_pattern_match_returns_none(self):
        retry = Retry(critical_error_exprs=["*fatal*"], ignore_error_exprs=["*timeout*"])
        assert retry._classify_error("some other error") is None

    def test_ignore_pattern_match_returns_ignored(self):
        retry = Retry(ignore_error_exprs=["*timeout*"])
        assert retry._classify_error("connection timeout") == RetryAction.SKIP

    def test_critical_pattern_match_returns_critical(self):
        retry = Retry(critical_error_exprs=["*fatal*"])
        assert retry._classify_error("fatal error") == RetryAction.ABORT

    def test_critical_takes_precedence_over_ignore(self):
        retry = Retry(critical_error_exprs=["*error*"], ignore_error_exprs=["*error*"])
        assert retry._classify_error("some error") == RetryAction.ABORT

    def test_exception_is_matched_by_its_text(self):
        retry = Retry(critical_error_exprs=["*boom*"])
        assert retry._classify_error(ValueError("boom happened")) == RetryAction.ABORT

    def test_match_is_case_sensitive(self):
        retry = Retry(critical_error_exprs=["*fatal*"])
        assert retry._classify_error("FATAL") is None

    def test_pattern_must_match_whole_text(self):
        retry = Retry(critical_error_exprs=["fatal"])
        assert retry._classify_error("fatal error") is None
        assert retry._classify_error("fatal") == RetryAction.ABORT

    def test_any_of_multiple_patterns_matches(self):
        retry = Retry(ignore_error_exprs=["*timeout*", "*503*"])
        assert retry._classify_error("HTTP 503") == RetryAction.SKIP

    def test_empty_message_is_not_none(self):
        assert Retry(ignore_error_exprs=["*"])._classify_error(ValueError()) == RetryAction.SKIP


class TestRetryRun:
    def test_success_sleeps_for_delay_and_increments_attempt(self, sleep):
        retry = Retry(max_retries=3, interval=1.0, backoff_rate=1.0)
        assert retry.run() == RetryAction.RETRY
        sleep.assert_called_once_with(1.0)
        assert retry._attempt == 1

    def test_unmatched_error_still_retries(self, sleep):
        retry = Retry(max_retries=1, critical_error_exprs=["*fatal*"])
        assert retry.run(error="transient") == RetryAction.RETRY
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
        assert retry.run() == RetryAction.RETRY
        assert retry.run() == RetryAction.RETRY
        with pytest.raises(RuntimeError, match="retry exhausted after 2 attempts"):
            retry.run()
        assert sleep.call_count == 2

    def test_exhausted_returns_result_and_warns_when_not_raising(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(max_retries=0, raise_on_exception=False, logstream=logstream)
        assert retry.run() == RetryAction.GIVE_UP
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
        assert retry.run(error="connection timeout") == RetryAction.SKIP
        sleep.assert_not_called()
        assert retry._attempt == 0

    def test_ignore_match_wins_over_exhausted(self, sleep):
        retry = Retry(max_retries=0, ignore_error_exprs=["*timeout*"])
        assert retry.run(error="connection timeout") == RetryAction.SKIP

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
        assert retry.run(error="fatal error") == RetryAction.ABORT
        sleep.assert_not_called()
        logstream.warning.assert_called_once()

    def test_critical_wins_over_exhausted(self, sleep):
        retry = Retry(max_retries=0, critical_error_exprs=["*fatal*"], raise_on_exception=False)
        assert retry.run(error="fatal error") == RetryAction.ABORT

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

    def test_skip_logs_debug_without_warning_or_error(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(ignore_error_exprs=["*timeout*"], logstream=logstream)
        retry.run(error="timeout")
        assert "skip retry" in logstream.debug.call_args.kwargs["msg"]
        logstream.warning.assert_not_called()
        logstream.error.assert_not_called()

    def test_abort_raising_logs_error_once(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(critical_error_exprs=["*fatal*"], logstream=logstream)
        with pytest.raises(RuntimeError):
            retry.run(error="fatal")
        logstream.error.assert_called_once()


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
        assert retry.run() == RetryAction.RETRY

    def test_reset_logs_debug_message(self):
        logstream = _mock_logstream()
        retry = Retry(logstream=logstream)
        retry.reset()
        logstream.debug.assert_called_once()
        assert "reset OK" in logstream.debug.call_args.kwargs["msg"]


class TestAttempt:
    def test_starts_not_done(self):
        assert Attempt(Retry()).done is False

    def test_enter_returns_self(self):
        _a = Attempt(Retry())
        with _a as _entered:
            assert _entered is _a

    def test_clean_exit_marks_done_without_sleeping(self, sleep):
        _a = Attempt(Retry())
        with _a:
            pass
        assert _a.done is True
        sleep.assert_not_called()

    def test_retryable_error_is_suppressed_and_not_done(self, sleep):
        retry = Retry(max_retries=1, interval=1.0)
        _a = Attempt(retry)
        with _a:
            raise ValueError("x")
        assert _a.done is False
        assert retry._attempt == 1
        sleep.assert_called_once_with(1.0)

    def test_skipped_error_is_suppressed_and_done(self, sleep):
        retry = Retry(ignore_error_exprs=["*timeout*"])
        _a = Attempt(retry)
        with _a:
            raise TimeoutError("timeout")
        assert _a.done is True
        sleep.assert_not_called()

    def test_give_up_without_raising_is_suppressed_and_done(self, sleep):
        _a = Attempt(Retry(max_retries=0, raise_on_exception=False))
        with _a:
            raise ValueError("x")
        assert _a.done is True

    def test_give_up_raising_propagates_original_exception(self, sleep):
        _err = ValueError("x")
        with pytest.raises(ValueError) as exc_info:
            with Attempt(Retry(max_retries=0)):
                raise _err
        assert exc_info.value is _err

    @pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit, GeneratorExit])
    def test_base_exception_propagates_without_retry(self, sleep, exc):
        retry = Retry(max_retries=3)
        _a = Attempt(retry)
        with pytest.raises(exc):
            with _a:
                raise exc()
        assert _a.done is False
        assert retry._attempt == 0
        sleep.assert_not_called()


class TestRetryAttempts:
    def test_yields_attempt_instances(self):
        for _a in Retry().attempts():
            assert isinstance(_a, Attempt)
            with _a:
                pass

    def test_is_lazy_and_resets_on_first_iteration(self):
        retry = Retry()
        retry._attempt = 2
        _gen = retry.attempts()
        assert retry._attempt == 2
        next(_gen)
        assert retry._attempt == 0

    def test_success_on_first_try_runs_once_without_sleeping(self, sleep):
        _fn = _Flaky([])
        assert _drive(Retry(max_retries=3), _fn) == "ok"
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_recovers_after_transient_failures(self, sleep):
        _fn = _Flaky([ValueError("a"), ValueError("b")])
        assert _drive(Retry(max_retries=3, interval=1.0), _fn) == "ok"
        assert _fn.calls == 3
        assert sleep.call_count == 2

    def test_success_on_last_allowed_retry(self, sleep):
        _fn = _Flaky([ValueError("a"), ValueError("b")])
        assert _drive(Retry(max_retries=2), _fn) == "ok"
        assert _fn.calls == 3

    def test_sleeps_follow_exponential_backoff(self, sleep):
        _fn = _Flaky([ValueError(str(i)) for i in range(3)])
        _drive(Retry(max_retries=3, interval=1.0, backoff_rate=2.0), _fn)
        assert _sleeps(sleep) == [1.0, 2.0, 4.0]
        assert _fn.calls == 4

    def test_exhaustion_raises_last_original_exception(self, sleep):
        _errs = [ValueError("a"), ValueError("b"), ValueError("c")]
        _fn = _Flaky(_errs)
        with pytest.raises(ValueError) as exc_info:
            _drive(Retry(max_retries=2), _fn)
        assert exc_info.value is _errs[-1]
        assert _fn.calls == 3
        assert sleep.call_count == 2

    def test_exhaustion_logs_error_once(self, sleep):
        logstream = _mock_logstream()
        with pytest.raises(ValueError):
            _drive(Retry(max_retries=1, logstream=logstream), _Flaky([ValueError("x")] * 5))
        logstream.error.assert_called_once()
        assert "retry exhausted after 1 attempts: x" in logstream.error.call_args.kwargs["msg"]

    def test_max_retries_zero_calls_once_then_raises(self, sleep):
        _fn = _Flaky([ValueError("x")] * 5)
        with pytest.raises(ValueError):
            _drive(Retry(max_retries=0), _fn)
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_exhaustion_without_raising_is_silent_and_stops(self, sleep):
        logstream = _mock_logstream()
        retry = Retry(max_retries=2, raise_on_exception=False, logstream=logstream)
        _fn = _Flaky([ValueError("x")] * 10)
        assert _drive(retry, _fn) is None
        assert _fn.calls == 3
        logstream.warning.assert_called_once()
        logstream.error.assert_not_called()

    def test_critical_error_aborts_immediately(self, sleep):
        _err = RuntimeError("fatal: disk")
        _fn = _Flaky([_err])
        with pytest.raises(RuntimeError) as exc_info:
            _drive(Retry(max_retries=5, critical_error_exprs=["*fatal*"]), _fn)
        assert exc_info.value is _err
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_critical_error_without_raising_stops_loop(self, sleep):
        retry = Retry(max_retries=5, critical_error_exprs=["*fatal*"], raise_on_exception=False)
        _fn = _Flaky([RuntimeError("fatal")] * 5)
        assert _drive(retry, _fn) is None
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_ignored_error_is_swallowed_without_retry(self, sleep):
        _fn = _Flaky([TimeoutError("timeout")] * 5)
        assert _drive(Retry(max_retries=5, ignore_error_exprs=["*timeout*"]), _fn) is None
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_unmatched_error_is_retried_when_patterns_configured(self, sleep):
        retry = Retry(max_retries=2, critical_error_exprs=["*fatal*"], ignore_error_exprs=["*timeout*"])
        _fn = _Flaky([ValueError("transient")])
        assert _drive(retry, _fn) == "ok"
        assert _fn.calls == 2

    def test_transient_then_ignored_stops_after_second_call(self, sleep):
        retry = Retry(max_retries=5, ignore_error_exprs=["*timeout*"])
        _fn = _Flaky([ValueError("transient")] + [TimeoutError("timeout")] * 5)
        assert _drive(retry, _fn) is None
        assert _fn.calls == 2
        assert sleep.call_count == 1

    def test_transient_then_critical_raises_after_second_call(self, sleep):
        retry = Retry(max_retries=5, critical_error_exprs=["*fatal*"])
        _fn = _Flaky([ValueError("transient"), RuntimeError("fatal")])
        with pytest.raises(RuntimeError, match="fatal"):
            _drive(retry, _fn)
        assert _fn.calls == 2

    def test_exception_text_is_used_for_pattern_matching(self, sleep):
        retry = Retry(ignore_error_exprs=["*503*"])
        assert _drive(retry, _Flaky([ConnectionError("HTTP 503 Service Unavailable")])) is None

    def test_base_exception_propagates_without_retry(self, sleep):
        _fn = _Flaky([KeyboardInterrupt()])
        with pytest.raises(KeyboardInterrupt):
            _drive(Retry(max_retries=5), _fn)
        assert _fn.calls == 1
        sleep.assert_not_called()

    def test_return_inside_with_stops_iteration(self, sleep):
        retry = Retry(max_retries=3)
        _calls = 0

        def _run() -> str:
            nonlocal _calls
            for attempt in retry.attempts():
                with attempt:
                    _calls += 1
                    return "early"
            return "unreachable"

        assert _run() == "early"
        assert _calls == 1

    def test_one_distinct_attempt_per_round_and_only_last_is_done(self, sleep):
        _fn = _Flaky([ValueError("a"), ValueError("b")])
        _seen: list[Attempt] = []
        for attempt in Retry(max_retries=3).attempts():
            _seen.append(attempt)
            with attempt:
                _fn()
        assert len(_seen) == 3
        assert len({id(a) for a in _seen}) == 3
        assert [a.done for a in _seen] == [False, False, True]

    def test_each_loop_starts_with_a_fresh_budget(self, sleep):
        retry = Retry(max_retries=1)
        assert _drive(retry, _Flaky([ValueError("a")])) == "ok"
        assert _drive(retry, _Flaky([ValueError("b")])) == "ok"

    def test_loop_after_exhaustion_starts_fresh(self, sleep):
        retry = Retry(max_retries=1)
        with pytest.raises(ValueError):
            _drive(retry, _Flaky([ValueError("x")] * 5))
        assert _drive(retry, _Flaky([])) == "ok"

    def test_independent_instances_can_be_nested(self, sleep):
        _inner_fn = _Flaky([ValueError("i")])
        _outer_fn = _Flaky([ValueError("o")])
        _results: list[str] = []
        for outer in Retry(max_retries=1).attempts():
            with outer:
                _outer_fn()
                _results.append(_drive(Retry(max_retries=1), _inner_fn))
        assert _results == ["ok"]
        assert _outer_fn.calls == 2
        assert _inner_fn.calls == 2
