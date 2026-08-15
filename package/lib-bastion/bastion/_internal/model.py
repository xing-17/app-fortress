from __future__ import annotations

import hashlib
import json
import uuid
from typing import ClassVar, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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
    def from_json(
        cls,
        data: dict,
    ) -> Self:
        """Create a model instance from a JSON dictionary."""
        return cls.model_validate(data)

    @classmethod
    def _generate_id(cls) -> str:
        """Return a new unique ID, optionally prefixed."""
        prefix = cls._id_prefix
        value = uuid.uuid4().hex[: cls._id_length]
        return f"{prefix}-{value}" if prefix else value

    @property
    def _logic_name(self) -> str:
        """Return a human-readable label used for logging and debugging."""
        _cls_name = self.__class__.__name__
        _id = self.id if self.id is not None else ""
        return f"{_cls_name}({_id})"

    @property
    def _sha256_key(self) -> str:
        return self.get_sha256_hash()

    def model_post_init(self, __context, /) -> None:
        """Auto-generate ID after model initialization if enabled."""
        if not self.id and self._id_enabled:
            self.id = self._generate_id()

    def get_sha256_hash(
        self,
        length: int = 24,
    ) -> str:
        _exported = self.export()
        _string = json.dumps(_exported, sort_keys=True)
        _hash = hashlib.sha256(_string.encode("utf-8")).hexdigest()
        return _hash[:length]

    def export(self) -> dict:
        """Export the model instance to a dictionary."""
        return self.model_dump()

    def describe(self) -> str:
        """Return a JSON string representation of the model."""
        return self.model_dump_json(
            indent=4,
            ensure_ascii=False,
        )
