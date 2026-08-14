from __future__ import annotations

import json


class IBastionObject:
    def export(self) -> dict:
        return {
            "__class__": self.__class__.__name__,
            "__module__": self.__class__.__module__,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
            default=str,
        )
