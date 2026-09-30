from __future__ import annotations

import time

from pydantic import Field

from app.resource.accessory._common._base import BaseAccessory


class Coolant(BaseAccessory):
    """
    Coolant accessory that pauses execution for a fixed interval.

    Args:
        interval (float): Cooling interval in seconds, default is 0.0

    Methods:
        run() -> None:
            Sleep for `interval` seconds if greater than 0, then log the result.

    """

    # Inherited from BaseAccessory
    # - id: str
    # - logstream: LogStream | None
    # - tags: dict[str, str]
    interval: float = Field(
        default=0.0,
        description="The cooling interval in seconds, default is 0.0.",
        ge=0,  # interval must be greater than or equal to 0
    )

    def run(self) -> None:
        if self.interval > 0:
            time.sleep(self.interval)
            self.debug(f"coolant {self.interval}s OK.")
