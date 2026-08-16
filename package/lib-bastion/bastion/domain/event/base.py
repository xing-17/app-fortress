from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseEventModel(IBastionModel):
    """
    Base event model for recording events that occurred during a run.

    Attributes:
        run_id (str): ID of the run associated with the event.
        message (str): Message content of the event.
        created_at (datetime): Datetime when the event was created.
        metadata (dict[str, Any]): Additional metadata related to the event.

    Methods:
        export(): Export the event as a dictionary with serialized fields.

    Example:
        ```python
        event = BaseEventModel(
            run_id="run-123",
            message="Task completed successfully"
        )
        exported = event.export()
        ```
    """

    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "event"
    _id_length: ClassVar[int] = 16
    run_id: str = Field(
        ...,
        description="ID of the run associated with the event.",
    )
    message: str | None = Field(
        default=None,
        description="Message content of the event.",
    )
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the event was created.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata related to the event.",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_required_datetime(cls, v: Any) -> Any:
        if v is None:
            return IBastionClock.current()
        if isinstance(v, str):
            return IBastionClock.from_iso(v)
        return v

    def export(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
