from __future__ import annotations

import hashlib
import json
from typing import Any, Self, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from pydantic_core import PydanticUndefined


class IAbstractDomain(BaseModel):
    """
    Abstract domain class for fortress.

    Methods:
        from_dict(value: dict | Self) -> Self:
            Create instance from dict or existing instance.

        sha256() -> str:
            Return SHA256 hash of the JSON representation of the instance.

        clone(**updates) -> Self:
            Create a deep copy with optional field updates.

        export() -> dict:
            Export the model instance to a JSON-serializable dictionary.

        describe() -> str:
            Return a JSON string representation of the model.

    """

    model_config = ConfigDict(
        frozen=False,
        extra="ignore",
        validate_assignment=True,
        populate_by_name=True,
    )

    @classmethod
    def from_dict(
        cls,
        value: dict | Self,
    ) -> Self:
        if isinstance(value, cls):
            return value
        return cls.model_validate(value)

    @model_validator(mode="before")
    @classmethod
    def _prepare(cls, data):
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

    def sha256(self) -> str:
        _encoded = self.describe().encode("utf-8")
        _value = hashlib.sha256(_encoded).hexdigest()
        return _value

    def clone(
        self,
        **updates,
    ) -> Self:
        return self.model_copy(
            update=updates,
            deep=True,
        )

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


class IAbstractTaggedDomain(IAbstractDomain):
    """
    Abstract tagged domain class for fortress

    Attributes:
        tags (dict[str, Any] | None): Tags associated with the domain.

    Methods:
        _non_override_tags() -> dict:
            Return a dictionary of tags that should not be overridden.

    """

    tags: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Tags associated with the domain",
    )

    def _non_override_tags(self) -> dict[str, Any]:
        return {}

    @model_validator(mode="after")
    def _update_tags(self):
        _base: dict = dict(self.tags or {})
        for k, v in self._non_override_tags().items():
            _base[k] = v
        object.__setattr__(self, "tags", _base)
        return self
