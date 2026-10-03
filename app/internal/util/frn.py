from __future__ import annotations

from app.internal.abstract.utility import IAbstractUtility


class IFrn(IAbstractUtility):
    @staticmethod
    def resolve(values: list[str]) -> str:
        _result: list[str] = []
        for item in values:
            if item:
                _result.append(item)
        return ":".join(_result)
