from __future__ import annotations

from app.internal.abstract.utility import IAbstractUtility


class IPartition(IAbstractUtility):
    @staticmethod
    def resolve(segments: list[str]) -> dict[str, str]:
        _parts: dict[str, str] = {}
        for segment in segments:
            if "=" not in segment:
                continue
            _k, _v = segment.split("=", 1)
            _k = _k.strip()
            _v = _v.strip()
            if _k and _v:
                _parts[_k] = _v
        return _parts
