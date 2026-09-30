from __future__ import annotations

import uuid

from app.internal.abstract.utility import IAbstractUtility


class IID(IAbstractUtility):
    @staticmethod
    def generate_id(
        length: int = 12,
        prefix: str | None = None,
    ) -> str:
        _id = str(uuid.uuid4())[:length]
        if prefix:
            return f"{prefix}{_id}"
        return _id
