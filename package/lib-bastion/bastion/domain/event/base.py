from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

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

    @classmethod
    def from_any(
        cls,
        value: dict | BaseEventModel,
    ) -> BaseEventModel:
        if isinstance(value, BaseEventModel):
            return value
        try:
            _attrs = {
                "id": value.get("id"),
                "run_id": value.get("run_id"),
                "message": value.get("message"),
                "created_at": IBastionClock.from_iso(value.get("created_at")),
                "metadata": value.get("metadata", {}),
            }
            return cls(**_attrs)
        except Exception as e:
            raise ValueError(f"Cannot create {cls.__name__}: {e}") from e

    def export(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
