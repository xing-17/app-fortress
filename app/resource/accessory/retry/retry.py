from __future__ import annotations

import time
from fnmatch import fnmatchcase

from pydantic import Field, PrivateAttr

from app.resource.accessory._common._base import BaseAccessory


class Retry(BaseAccessory):
    """
    Retry accessory that performs exponential backoff with configurable parameters.

    Args:
    -----------
        max_retries(int):
            Maximum number of retry attempts.
        interval(float):
            Base interval in seconds for attempt 0.
        backoff_rate(float):
            Growth multiplier applied per retry attempt.
        raise_on_exhausted(bool):
            Whether to raise an exception when the maximum number of retries is reached.
        critical_error_exprs(list[str]):
            List of string expression patterns for critical errors.
        ignore_error_exprs(list[str]):
            List of string expression patterns for errors to ignore.

    Methods:
    -----------
        run(error: Exception | str | None = None) -> None:
            Perform the backoff delay based on the current attempt count.
            If `error` matches `critical_error_exprs`, re-raise it immediately without retrying.
            If `error` matches `ignore_error_exprs`, return without consuming an attempt.
            Raises RuntimeError if the maximum number of retries is reached and `raise_on_exhausted` is True.
        reset() -> None:
            Reset the internal attempt counter back to 0.

    """

    # Inherited from BaseAccessory
    # - id: str
    # - logstream: LogStream | None
    # - tags: dict[str, str]
    max_retries: int = Field(
        default=1,
        description="[Optional] Maximum number of retry attempts.",
        ge=0,
    )
    interval: float = Field(
        default=5,
        description="Base interval in seconds for attempt 0.",
        ge=0,
    )
    backoff_rate: float = Field(
        default=1.0,
        description="[Optional] Growth multiplier applied per retry attempt.",
        ge=0,
    )
    raise_on_exhausted: bool = Field(
        default=True,
        description="[Optional] Whether to raise an exception when exhausted.",
    )
    critical_error_exprs: list[str] = Field(
        default_factory=list,
        description="[Optional] List of string expression patterns for critical errors.",
    )  # example: "*error*"
    ignore_error_exprs: list[str] = Field(
        default_factory=list,
        description="[Optional] List of string expression patterns for errors to ignore.",
    )  # example: "*error*"

    _attempt: int = PrivateAttr(default=0)

    def _should_retry(
        self,
        error: Exception | str | None = None,
    ) -> bool:
        if error is None:
            return True
        _msg = str(error)
        if any(fnmatchcase(_msg, _p) for _p in self.critical_error_exprs):
            self.error(f"critical error matched, abort retry: {_msg}")
            raise RuntimeError(_msg) if isinstance(error, str) else error
        if any(fnmatchcase(_msg, _p) for _p in self.ignore_error_exprs):
            self.debug(f"ignorable error matched, skip retry: {_msg}")
            return False
        return True

    def _delay(self) -> float:
        _duration: float = self.interval * (self.backoff_rate**self._attempt)
        return round(_duration, 3)

    def run(
        self,
        error: Exception | str | None = None,
    ) -> None:
        if not self._should_retry(error):
            return

        if self._attempt >= self.max_retries:
            _msg = f"retry exhausted after {self._attempt} attempts"
            if self.raise_on_exhausted:
                self.error(_msg)
                raise RuntimeError(_msg)
            else:
                self.warning(_msg)
                return

        # Perform the backoff delay for the current attempt.
        _seconds = self._delay()
        time.sleep(_seconds)
        self._attempt += 1
        self.debug(f"retry attempt={self._attempt} {_seconds}s OK.")

    def reset(self) -> None:
        self._attempt = 0
        self.debug("reset OK.")
