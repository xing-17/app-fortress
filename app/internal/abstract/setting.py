from __future__ import annotations

import json
from pathlib import Path
from typing import Self, get_args

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticUndefined


class IAbstractSetting(BaseModel):
    """
    Abstract Setting class for fortress

    Attributes:
        kind: (str)
            Setting kind, automatically derived from the class name.

    Methods:
        from_yaml(path: str | Path) -> IAbstractSetting:
            Load settings from a YAML file.

        from_dict(data: dict) -> IAbstractSetting:
            Load settings from a dictionary.

        export() -> dict:
            Export settings to a dictionary.

        describe() -> str:
            Return a JSON string representation of the settings.

    """

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> Self:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"YAML not found: {resolved}")

        try:
            with resolved.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to read YAML: {e}") from e

        return cls(**data)

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> Self:
        return cls(**data)

    @model_validator(mode="before")
    @classmethod
    def _prepare(cls, data) -> dict:
        if isinstance(data, dict):
            data = dict(data)

            for name, field_info in cls.model_fields.items():
                if name not in data:
                    continue
                if data[name] is not None:
                    continue

                # Check if fields has a default value or default factory
                _has_factory = field_info.default_factory is not None
                _not_undefined = field_info.default is not PydanticUndefined
                _has_default = _has_factory or _not_undefined

                # Check if the field accepts None
                _accepts_none = type(None) in get_args(field_info.annotation)

                # Only remove the field if it has a default and does not accept None
                if _has_default and not _accepts_none:
                    del data[name]

        return data

    @property
    def cls_name(self) -> str:
        return str(self.__class__.__name__).lower()

    def export(self) -> dict:
        return self.model_dump(
            mode="json",
            round_trip=True,
        )

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
            sort_keys=True,
        )


class IAbstractTaggedSetting(IAbstractSetting):
    """
    Abstract tagged setting class for fortress

    Attributes:
        tags (dict[str, str]): Tags associated with the setting.

    """

    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the setting",
    )

    def _non_override_tags(self) -> dict[str, str]:
        return {}

    @model_validator(mode="after")
    def _update_tags(self):
        _base: dict = dict(self.tags or {})
        for k, v in self._non_override_tags().items():
            _base[k] = v
        object.__setattr__(self, "tags", _base)
        return self
