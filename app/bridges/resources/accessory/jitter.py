from __future__ import annotations

import random
import time
from typing import Any

from app.bridges.resources.accessory.base import BaseAccessory


class Jitter(BaseAccessory):
    """
    随机延迟抖动器。

    Attributes:
        min_seconds: 最短延迟秒数, None 表示未配置
        max_seconds: 最长延迟秒数, None 表示未配置
        is_enabled:  两端均有效时为 True, 否则 jit() 不执行任何操作

    Examples:
        >>> j = Jitter(min_seconds=0.5, max_seconds=1.5)
        >>> j.jit()  # sleep 0.5 ~ 1.5 秒

        >>> j = Jitter()   # 未配置, is_enabled=False
        >>> j.jit()        # 立即返回, 无 sleep
    """

    def __init__(
        self,
        min_seconds: float | int | None = None,
        max_seconds: float | int | None = None,
    ) -> None:
        super().__init__()
        self.min_seconds: float | None = self._resolve_seconds(min_seconds)
        self.max_seconds: float | None = self._resolve_seconds(max_seconds)
        self._validate()
        self._set_log_prefix(f"Jitter({self.uuid})")

    def _resolve_seconds(
        self,
        value: float | int | None = None,
    ) -> float | None:
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid value for seconds: {value}") from e
        if value < 0.0:
            raise ValueError(f"Seconds value cannot be negative: {value}")
        return value

    @property
    def is_enabled(self) -> bool:
        _valid_min = self.min_seconds is not None
        _valid_max = self.max_seconds is not None
        return _valid_min and _valid_max

    def _validate(self) -> None:
        if self.min_seconds is None and self.max_seconds is None:
            return
        if self.min_seconds is None or self.max_seconds is None:
            raise ValueError("min_seconds and max_seconds must be both set")
        if self.min_seconds >= self.max_seconds:
            raise ValueError("min_seconds must be < max_seconds")

    def jit(self) -> float | None:
        if self.is_enabled:
            delay = random.uniform(self.min_seconds, self.max_seconds)
            delay_rounded = round(delay, 3)
            time.sleep(delay_rounded)
            self.debug(f"jit: delay {delay_rounded} seconds")
            return delay_rounded
        else:
            return None

    def export(self) -> dict[str, Any]:
        result = super().export()
        result.update(
            {
                "min_seconds": self.min_seconds,
                "max_seconds": self.max_seconds,
                "is_enabled": self.is_enabled,
            }
        )
        return result
