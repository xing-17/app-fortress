from __future__ import annotations

import time

from pydantic import Field, PrivateAttr

from app.resource.accessory._common._base import BaseAccessory


class Backoff(BaseAccessory):
    """
    Exponential backoff accessory.

    Args:
    -----------
        interval(float):
            Base interval in seconds for attempt 0.
        rate(float):
            Growth multiplier applied per retry attempt.
        max_retries(int):
            Maximum number of retry attempts.
        raise_on_max_retries(bool):
            Whether to raise an exception when the maximum number of retries is reached.

    Methods:
    -----------
        run() -> None:
            Perform the backoff delay based on the current attempt count.
            Raises RuntimeError if the maximum number of retries is reached and `raise_on_max_retries` is True.

    """

    # Inherited from BaseAccessory
    # - id: str
    # - logstream: LogStream | None
    # - tags: dict[str, str]
    interval: float = Field(
        default=5,
        description="Base interval in seconds for attempt 0.",
        ge=0,
    )
    rate: float = Field(
        default=1.0,
        description="[Optional] Growth multiplier applied per retry attempt.",
        ge=0,
    )
    max_retries: int = Field(
        default=3,
        description="[Optional] Maximum number of retry attempts.",
        ge=0,
    )
    raise_on_max_retries: bool = Field(
        default=True,
        description="[Optional] Whether to raise an exception when the maximum number of retries is reached.",
    )

    _attempt: int = PrivateAttr(default=0)

    def _add_attempt(self) -> None:
        self._attempt += 1

    def _delay(self) -> float:
        _duration: float = self.interval * (self.rate**self._attempt)
        return round(_duration, 3)

    def run(self) -> None:
        if self._attempt >= self.max_retries:
            _msg = f"backoff exhausted after {self._attempt} attempts"
            if self.raise_on_max_retries:
                self.error(_msg)
                raise RuntimeError(_msg)
            else:
                self.warning(_msg)
                return

        # Perform the backoff delay for the current attempt.
        _seconds = self._delay()
        time.sleep(_seconds)
        self._add_attempt()
        self.debug(f"backoff attempt={self._attempt} {_seconds}s OK.")
