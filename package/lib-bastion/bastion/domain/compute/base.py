from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class ComputeKind(StrEnum):
    LOCAL_PY_FN = "local_py_fn"

    @classmethod
    def from_any(
        cls,
        value: str | ComputeKind,
    ) -> ComputeKind:
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid ComputeKind value: {value}")


class BaseComputeModel(IBastionModel):
    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the compute resource",
    )
    kind: ComputeKind = Field(
        ...,
        description="Kind of the compute resource, e.g., 'docker', 'local_py_fn', etc.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the compute resource",
    )

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "tags": self.tags,
        }
