from __future__ import annotations

from app.internal.abstract.utility import IAbstractUtility


class IPartition(IAbstractUtility):
    @staticmethod
    def resolve(segments: list[str]) -> dict[str, str]:
        # Convert a list of "key=value" segments into a dictionary
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

    @staticmethod
    def to_string(
        partitions: dict[str, str],
        connector: str = "/",
    ) -> str:
        # Return a=1/b=2/c=3
        if not partitions:
            return ""
        if not connector:
            connector = "/"
        _segments: list[str] = [f"{k}={v}" for k, v in partitions.items()]
        _result: str = connector.join(_segments)
        return _result

    @staticmethod
    def to_pattern(
        partitions: list[str],
        connector: str = "/",
    ) -> str:
        # Return a=*/b=*
        if not partitions:
            return "*"
        if not connector:
            connector = "/"
        _segments: list[str] = [f"{p}=*" for p in partitions]
        _pattern: str = connector.join(_segments)
        return _pattern
