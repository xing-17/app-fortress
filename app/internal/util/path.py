from __future__ import annotations

from pathlib import Path

import yaml

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
        _value = IPath.resolve(value)
        if not _value.exists():
            raise ValueError(f"IPath: path does not exist: {_value}")
        return _value

    @staticmethod
    def validate_yaml(value: Path | str) -> Path:
        _value = IPath.validate_exists(value)
        try:
            with open(_value, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"IPath: {_value} is not valid YAML") from e
        return _value
