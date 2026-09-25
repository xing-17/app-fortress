from __future__ import annotations

from app.internal.abstract.utility import IAbstractUtility


class IPrefix(IAbstractUtility):
    @staticmethod
    def resolve(value: str | None) -> str:
        _value = value or ""
        return _value.rstrip("/")
