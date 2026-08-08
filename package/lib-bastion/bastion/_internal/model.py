from __future__ import annotations

import uuid
from typing import ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class IBastionModel(BaseModel):
    """Base model for all Bastion domain objects.

    Provides automatic ID generation, a human-readable identity label,
    and serialization helpers. Subclasses can customise the ID format
    by overriding ``_id_prefix`` and ``_id_length``.

    Class Variables:
        _id_prefix: Optional prefix prepended to the generated ID (e.g. ``"ast"`` → ``"ast-a3f9"``).  Defaults to no prefix.
        _id_length: Number of hex characters taken from UUID4.  Defaults to 12.

    Attributes:
        id: Unique identifier, auto-generated on instantiation when left empty.

    Example::

        class MyAsset(IBastionModel):
            _id_prefix = "ast"
            name: str

        asset = MyAsset(name="orders")
        print(asset.id)       # "ast-a3f9c1..."
        print(asset.describe())
    """

    _id_prefix: ClassVar[str] = ""
    _id_length: ClassVar[int] = 12
    id: str = Field(default="")
    model_config = ConfigDict(frozen=False)

    @classmethod
    def _generate_id(cls) -> str:
        """Return a new unique ID, optionally prefixed."""
        prefix = cls._id_prefix
        value = uuid.uuid4().hex[: cls._id_length]
        return f"{prefix}-{value}" if prefix else value

    @property
    def _logic_name(self) -> str:
        """Human-readable label used for logging and debugging."""
        _cls_name = self.__class__.__name__
        _id = self.id if self.id is not None else ""
        return f"{_cls_name}({_id})"

    def model_post_init(self, __context, /) -> None:
        if self.id is None:
            self.id = self._generate_id()

    def export(self) -> dict:
        """Return the model as a plain dictionary suitable for storage."""
        return self.model_dump()

    def describe(self) -> str:
        """Return a pretty-printed JSON representation of the model."""
        return self.model_dump_json(
            indent=4,
            ensure_ascii=False,
            default=str,
        )
