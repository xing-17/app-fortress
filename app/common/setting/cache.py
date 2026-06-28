from __future__ import annotations

import json

from pydantic import BaseModel


class CacheSetting(BaseModel):
    name: str = "cache"
    url: str = "sqlite:///cache/system/cache.db"
    chunksize: int | None = None

    def export(self) -> dict:
        return self.model_dump()

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
