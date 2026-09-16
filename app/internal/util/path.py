from __future__ import annotations

from pathlib import Path

from app.internal.abstract.utility import IAbstractUtility


class IPath(IAbstractUtility):
    """
    Path Utility for local system operations.

    Methods:
        resolve(value: Path | str) -> Path:
            Resolve the given value to a Path object.

    """

    @staticmethod
    def resolve(
        value: Path | str,
        default: Path | None = None,
        validate: bool = False,
    ) -> Path:
        if not value:
            if default is None:
                raise ValueError("IPath: path can not be None or empty")
            else:
                value = default
        _result = Path(value).expanduser().resolve()
        if validate and not _result.exists():
            raise ValueError(f"IPath: path does not exist: {_result}")
        return _result

    @staticmethod
    def validate_exists(value: Path | str) -> Path:
        path = IPath.resolve(value)
        if not path.exists():
            raise ValueError(f"IPath: path does not exist: {path}")
        return path
