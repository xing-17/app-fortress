from __future__ import annotations

import hashlib
import uuid
from typing import ClassVar, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class IBastionModel(BaseModel):
    """
    Base Pydantic model with auto-generated ID and serialization utilities.

    Attributes:
        id (str): Unique identifier for the model instance, auto-generated if not provided.

    Methods:
        from_json(dict data): Creates a model instance from a JSON dictionary.
        export(): Exports the model instance to a dictionary.
        describe(): Returns a JSON string representation of the model.

    Example:
        ```python
        from bastion._internal.model import IBastionModel

        class MyModel(IBastionModel):
            _id_prefix = "my"
            name: str

        # Create instance with auto-generated ID
        obj = MyModel(name="example")
        print(obj.id)  # e.g., "my-a1b2c3d4e5f6"

        # Create from JSON
        obj2 = MyModel.from_json({"name": "test", "id": "my-123456"})
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
    def from_any(
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
    def logic_name(self) -> str:
        _cls_name = self.__class__.__name__
        _id = self.id if self.id is not None else ""
        return f"{_cls_name}({_id})"

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
        return self.model_dump(mode="json")

    def describe(self) -> str:
        return self.model_dump_json(
            indent=4,
            ensure_ascii=False,
        )
