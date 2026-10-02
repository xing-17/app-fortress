from __future__ import annotations

from app.internal.abstract.utility import IAbstractUtility


class IPrefix(IAbstractUtility):
    @staticmethod
    def resolve(
        value: str | None,
        default: str | None = None,
    ) -> str:
        _value = value or default or ""
        return _value.strip("/")

    @staticmethod
    def validate_key(value: str) -> None:
        if not value:
            raise ValueError("Key cannot be empty.")
        if value.endswith("/"):
            raise ValueError("Key cannot end with a slash.")
