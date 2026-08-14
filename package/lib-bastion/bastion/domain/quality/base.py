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
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the quality metrics were created.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of quality metrics.",
    )

    def export(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics,
        }
