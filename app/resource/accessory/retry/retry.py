from __future__ import annotations

import time
from enum import StrEnum
from fnmatch import fnmatchcase

from pydantic import Field, PrivateAttr

from app.resource.accessory._common._base import BaseAccessory


class RetryResult(StrEnum):
    """
    Outcome of a single `Retry.run()` call.

    Members:
    -----------
        SUCCESS:
            Backoff delay elapsed; the caller may attempt again.
        IGNORED:
            Error matched an ignore pattern; skip retrying.
        CRITICAL:
            Error matched a critical pattern; abort.
        EXHAUSTED:
            No retries left.

    """

    CRITICAL = "CRITICAL"
    IGNORED = "IGNORED"
    EXHAUSTED = "EXHAUSTED"
    SUCCESS = "SUCCESS"


class Retry(BaseAccessory):
    """
    Retry controller with error classification and exponential backoff.

    Delay before retry n (0-based) is `interval * backoff_rate ** n`, rounded to 3 decimals.

    Args:
    -----------
        max_retries (int):
            Maximum number of retries after the initial call.
        interval (float):
            Base interval in seconds for attempt 0.
        backoff_rate (float):
            Growth multiplier applied per retry attempt.
        raise_on_exception (bool):
            Raise on critical errors or exhausted retries; otherwise log a warning and return the result.
        critical_error_exprs (list[str]):
            Glob patterns (fnmatch, case-sensitive) matched against the error text; abort on match.
        ignore_error_exprs (list[str]):
            Glob patterns (fnmatch, case-sensitive) matched against the error text; skip retry on match.

    Methods:
    -----------
        run(error: Exception | str | None = None) -> RetryResult:
            Classify the error, then sleep and consume one retry if allowed.
            Critical takes precedence over ignored; both are checked before the retry limit.
            Returns SUCCESS, IGNORED, CRITICAL or EXHAUSTED.
            Raises the original exception (or RuntimeError for str/None) on CRITICAL or
            EXHAUSTED when raise_on_exception is True.
        reset() -> None:
            Reset the retry counter for a new operation.

    """

    # [Inherited] id: str
    # [Inherited] logstream: LogStream | None
    # [Inherited] tags: dict[str, str]
    max_retries: int = Field(
        default=1,
        description="[Optional] Maximum number of retries after the initial call.",
        ge=0,
    )
    interval: float = Field(
        default=5,
        description="[Optional] Base interval in seconds for attempt 0.",
        ge=0,
        allow_inf_nan=False,
    )
    backoff_rate: float = Field(
        default=1.0,
        description="[Optional] Growth multiplier applied per retry attempt.",
        ge=0,
        allow_inf_nan=False,
    )
    raise_on_exception: bool = Field(
        default=True,
        description="[Optional] Raise on critical errors or exhausted retries.",
    )
    critical_error_exprs: list[str] = Field(
        default_factory=list,
        description="[Optional] Critical error patterns matched against error text.",
    )
    ignore_error_exprs: list[str] = Field(
        default_factory=list,
        description="[Optional] Ignored error patterns matched against error text.",
    )

    _attempt: int = PrivateAttr(default=0)

    def _classify_error(
        self,
        error: Exception | str | None = None,
    ) -> RetryResult | None:
        if error is None:
            return None
        _msg: str = str(error)
        if any(fnmatchcase(_msg, _p) for _p in self.critical_error_exprs):
            return RetryResult.CRITICAL
        if any(fnmatchcase(_msg, _p) for _p in self.ignore_error_exprs):
            return RetryResult.IGNORED
        return None

    def _delay(self) -> float:
        _duration: float = self.interval * (self.backoff_rate**self._attempt)
        return round(_duration, 3)

    def _handle_failure(
        self,
        result: RetryResult,
        message: str,
        error: Exception | str | None = None,
    ) -> RetryResult:
        if self.raise_on_exception:
            self.error(message)
            if isinstance(error, Exception):
                raise error
            raise RuntimeError(message)
        self.warning(message)
        return result

    def run(
        self,
        error: Exception | str | None = None,
    ) -> RetryResult:
        _result: RetryResult | None = self._classify_error(error)
        if _result == RetryResult.CRITICAL:
            return self._handle_failure(
                result=RetryResult.CRITICAL,
                message=f"critical error matched, abort retry: {error}",
                error=error,
            )
        if _result == RetryResult.IGNORED:
            self.debug(f"ignorable error matched, skip retry: {error}")
            return RetryResult.IGNORED
        if self._attempt >= self.max_retries:
            _msg: str = f"retry exhausted after {self._attempt} attempts"
            if error is not None:
                _msg = f"{_msg}: {error}"
            return self._handle_failure(
                result=RetryResult.EXHAUSTED,
                message=_msg,
                error=error,
            )

        _seconds: float = self._delay()
        time.sleep(_seconds)
        self._attempt += 1
        self.debug(f"retry attempt={self._attempt} delay={_seconds}s OK.")
        return RetryResult.SUCCESS

    def reset(self) -> None:
        self._attempt = 0
        self.debug("reset OK.")
