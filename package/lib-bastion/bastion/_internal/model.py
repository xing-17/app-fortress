from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from bastion._internal.clock import IBastionClock


class IBastionModel(BaseModel):
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
        """
        Create a model instance from a JSON dictionary.
        """
        return cls.model_validate(data)

    @classmethod
    def _generate_id(cls) -> str:
        """
        Return a new unique ID, optionally prefixed.
        """
        prefix = cls._id_prefix
        value = uuid.uuid4().hex[: cls._id_length]
        return f"{prefix}-{value}" if prefix else value

    @property
    def _logic_name(self) -> str:
        """
        Human-readable label used for logging and debugging.
        """
        _cls_name = self.__class__.__name__
        _id = self.id if self.id is not None else ""
        return f"{_cls_name}({_id})"

    def model_post_init(self, __context, /) -> None:
        if not self.id and self._id_enabled:
            self.id = self._generate_id()

    def export(self) -> dict:
        return self.model_dump()

    def describe(self) -> str:
        return self.model_dump_json(
            indent=4,
            ensure_ascii=False,
            default=str,
        )
