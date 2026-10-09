from __future__ import annotations

import random
import time

from pydantic import Field

from app.resource.accessory._common._base import BaseAccessory


class Jitter(BaseAccessory):
    """
    Jitter accessory that pauses execution for a random interval.

    Args:
    -----------
        min_seconds (float):
            Minimum number of seconds for the jitter delay, default is 0.0
        max_seconds (float):
            Maximum number of seconds for the jitter delay, default is 1.0

    Methods:
    -----------
        run() -> None:
            Sleep for a random duration in [min_seconds, max_seconds] if valid, then log the result.

    """

    # Inherited from BaseAccessory
    # - id: str
    # - logstream: LogStream | None
    # - tags: dict[str, str]
    min_seconds: float = Field(
        default=0.0,
        description="The minimum number of seconds for the jitter delay, default is 0.0",
        ge=0,  # must be greater than or equal to 0
    )
    max_seconds: float = Field(
        default=0.5,
        description="The maximum number of seconds for the jitter delay, default is 0.5",
        ge=0,  # must be greater than or equal to 0
    )

    def run(self) -> None:
        if self.min_seconds >= 0.0 and self.max_seconds > 0.0:
            _interval = random.uniform(self.min_seconds, self.max_seconds)
            _rounded = round(_interval, 3)
            time.sleep(_rounded)
            self.debug(f"jit {_rounded}s OK.")
