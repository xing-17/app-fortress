from __future__ import annotations

import time
from typing import Any, Literal

from app.bridges.resources.accessory.base import BaseAccessory


class Coolant(BaseAccessory):
    """
    冷却器

    Attributes:
        interval: 冷却时间间隔, 单位秒, 默认 0.0。

    Examples:
        >>> c = Coolant(interval=1.5)
        >>> c.run()  # sleep 1.5 秒

    """

    _default_interval: float = 0.0

    def __init__(
        self,
        interval: float | int | None = None,
    ) -> None:
        super().__init__()
        self.interval: float = self._resolve_interval(
            value=interval,
            default=self._default_interval,
        )
        self._set_log_prefix(f"Coolant({self.uuid})")

    def _resolve_interval(
        self,
        value: float | int | None,
        default: float,
    ) -> float:
        if value is None:
            return default
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"interval must be > 0 number, got {value}")
        return float(value)

    def run(self) -> None:
        if self.interval > 0:
            time.sleep(self.interval)
            self.debug(f"run: sleep {self.interval:.3f}s.")

    def __enter__(self) -> Coolant:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> Literal[False]:
        return False

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["interval"] = self.interval
        return result
