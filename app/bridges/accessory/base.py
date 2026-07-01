from __future__ import annotations

import json

from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class BaseAccessory(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    def __init__(self):
        super().__init__()
        self.klass = str(self.__class__.__name__).lower()

    def export(self) -> dict[str, any]:
        return {
            "klass": self.klass,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
