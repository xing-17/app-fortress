from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseQualityModel(IBastionModel):
    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "qual"
    _id_length: ClassVar[int] = 20

    run_id: str = Field(
        ...,
        description="ID of the run associated with the quality metrics.",
    )
    kind: str = Field(
        default="base",
        description="Kind of the model, fixed to 'quality'.",
    )
    passed: bool = Field(
        default=True,
        description="Indicates whether the quality check passed.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the quality metrics.",
    )
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the quality metrics were created.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of quality metrics.",
    )

    @classmethod
    def from_any(
        cls,
        value: dict | BaseQualityModel,
    ) -> BaseQualityModel:
        if isinstance(value, BaseQualityModel):
            return value
        try:
            _attrs = {
                "id": value.get("id"),
                "run_id": value.get("run_id"),
                "kind": value.get("kind", "base"),
                "passed": value.get("passed", True),
                "description": value.get("description", None),
                "created_at": IBastionClock.from_iso(value.get("created_at")),
                "metrics": value.get("metrics", {}),
            }
            _attrs = {k: v for k, v in _attrs.items() if v is not None}
            return cls(**_attrs)
        except Exception as e:
            raise ValueError(f"Cannot create {cls.__name__}: {e}") from e

    def export(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "kind": self.kind,
            "passed": self.passed,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics,
        }
