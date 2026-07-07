from __future__ import annotations

import json
import uuid

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
        self.uuid = self._get_uuid()

    def _get_uuid(self) -> str:
        return str(uuid.uuid4())[:8]

    def export(self) -> dict[str, any]:
        return {
            "klass": self.klass,
            "uuid": self.uuid,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
