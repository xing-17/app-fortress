from __future__ import annotations

import hashlib
import uuid
from typing import ClassVar, Self, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class IDomain(BaseModel):
    """
    Base Pydantic model with auto-generated ID and serialization utilities.

    Attributes:
        id (str): Unique identifier for the model instance, auto-generated if not provided.
        _id_enabled (ClassVar[bool]): Whether to enable auto-generated IDs.
        _id_prefix (ClassVar[str]): Prefix for auto-generated IDs.
        _id_length (ClassVar[int]): Length of the generated UUID portion.

    Methods:
        from_dict(dict | Self value): Create instance from dict or existing instance.
        clone(**updates): Create a deep copy with optional field updates.
        export(): Export the model instance to a JSON-serializable dictionary.
        describe(): Return a JSON string representation of the model.
        logic_name: Property returning a formatted name with class and ID.

    Example:
        ```python
        from bastion.internal.imodel import IDomain

        class MyModel(IDomain):
            _id_prefix = "my"
            name: str

        # Create instance with auto-generated ID
        obj = MyModel(name="example")
        print(obj.id)  # e.g., "my-a1b2c3d4e5f6"

        # Create from dict
        obj2 = MyModel.from_dict({"name": "test", "id": "my-123456"})

        # Clone with updates
        obj3 = obj.clone(name="updated")

        # Export and describe
        data = obj.export()
        json_str = obj.describe()

        ```
    """

    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = ""
    _id_length: ClassVar[int] = 12
    id: str = Field(
        default="",
        description="Unique identifier for the model instance",
    )
    model_config = ConfigDict(
        frozen=False,
        extra="ignore",
        validate_assignment=True,
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
            # Create a copy to avoid mutating the original dictionary
            data = dict(data)

            # None on a non-optional field
            # ! → treat as absent so factory activates
            for name, field_info in cls.model_fields.items():
                if name in data and data[name] is None:
                    if type(None) not in get_args(field_info.annotation):
                        del data[name]

            # Generate an ID if it's enabled and not provided
            if cls._id_enabled and not data.get("id"):
                data["id"] = cls._generate_id()

        return data

    @classmethod
    def _generate_id(cls) -> str:
        prefix = cls._id_prefix
        value = uuid.uuid4().hex[: cls._id_length]
        return f"{prefix}-{value}" if prefix else value

    @property
    def sha256(self) -> str:
        _string = self.model_dump_json(
            indent=4,
            ensure_ascii=False,
        )
        return hashlib.sha256(_string.encode("utf-8")).hexdigest()

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
        )

    def describe(self) -> str:
        return self.model_dump_json(
            indent=4,
            ensure_ascii=False,
        )
