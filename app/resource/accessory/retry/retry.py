from __future__ import annotations

import time
from collections.abc import Iterator
from enum import StrEnum
from fnmatch import fnmatchcase

from pydantic import Field, PrivateAttr

from app.resource.accessory._common._base import BaseAccessory


class RetryAction(StrEnum):
    """
    Outcome of a single `Retry.run()` call.

    Members:
    -----------
        RETRY:
            Backoff delay elapsed; the caller may attempt again.
        SKIP:
            Error matched an ignore pattern; skip retrying.
        ABORT:
            Error matched a critical pattern; abort.
        GIVE_UP:
            No retries left; give up.

    """

    ABORT = "ABORT"
    SKIP = "SKIP"
    GIVE_UP = "GIVE_UP"
    RETRY = "RETRY"


class Attempt:
    """
    Attempt object within a retry object.

    Attributes:
    ----------
        done (bool):
            Indicates whether this attempt has completed (either successfully or not).

    Args:
    ----------
        retry (Retry):
            The parent retry object managing this attempt.

    Methods:
    ----------
        __enter__() -> Attempt:
            Enter the runtime context related to this attempt.
        __exit__(exc_type, exc_value, tb) -> bool:
            Exit the runtime context, handling the error classification and retry logic.

    """

    def __init__(
        self,
        retry: Retry,
    ) -> None:
        self._retry = retry
        self.done = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if not isinstance(exc_value, Exception):
            # if none: success;
            # if Exception: re-raise as is
            self.done = exc_value is None
            return False
        else:
            # if RETRY: can retry again
            # if SKIP / GIVE_UP / ABORT: stop retrying
            _res: RetryAction = self._retry.run(error=exc_value)
            self.done = _res != RetryAction.RETRY
            return True


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
        run(error: Exception | str | None = None) -> RetryAction:
            Classify the error, then sleep and consume one retry if allowed.
            Critical takes precedence over ignored; both are checked before the retry limit.
            Returns RETRY, SKIP, ABORT or GIVE_UP.
            Raises the original exception (or RuntimeError for str/None) on ABORT or
            GIVE_UP when raise_on_exception is True.
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
    ) -> RetryAction | None:
        if error is None:
            return None
        _msg: str = str(error)
        if any(fnmatchcase(_msg, _p) for _p in self.critical_error_exprs):
            return RetryAction.ABORT
        if any(fnmatchcase(_msg, _p) for _p in self.ignore_error_exprs):
            return RetryAction.SKIP
        return None

    def _delay(self) -> float:
        _duration: float = self.interval * (self.backoff_rate**self._attempt)
        return round(_duration, 3)

    def _handle_failure(
        self,
        result: RetryAction,
        message: str,
        error: Exception | str | None = None,
    ) -> RetryAction:
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
    ) -> RetryAction:
        _result: RetryAction | None = self._classify_error(error)
        if _result == RetryAction.ABORT:
            return self._handle_failure(
                result=RetryAction.ABORT,
                message=f"critical error matched, abort retry: {error}",
                error=error,
            )
        if _result == RetryAction.SKIP:
            self.debug(f"ignorable error matched, skip retry: {error}")
            return RetryAction.SKIP
        if self._attempt >= self.max_retries:
            _msg: str = f"retry exhausted after {self._attempt} attempts"
            if error is not None:
                _msg = f"{_msg}: {error}"
            return self._handle_failure(
                result=RetryAction.GIVE_UP,
                message=_msg,
                error=error,
            )

        _seconds: float = self._delay()
        time.sleep(_seconds)
        self._attempt += 1
        self.debug(f"retry attempt={self._attempt} delay={_seconds}s OK.")
        return RetryAction.RETRY

    def attempts(self) -> Iterator["Attempt"]:
        self.reset()
        while True:
            _attempt = Attempt(self)
            yield _attempt
            if _attempt.done:
                return

    def reset(self) -> None:
        self._attempt = 0
        self.debug("reset OK.")
