from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class EventKind(StrEnum):
    """
    Event kind enumeration for categorizing different types of events.

    Attributes:
        BASE (str): Base event kind.

    Methods:
        from_any(value): Convert string or EventKind to EventKind instance.

    Example:
        ```python
        kind = EventKind.BASE
        kind_from_str = EventKind.from_any("base")
        ```
    """

    BASE = "base"

    @classmethod
    def from_any(
        cls,
        value: str | EventKind,
    ) -> EventKind:
        """
        Convert string or EventKind instance to EventKind.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid EventKind value: {value}")


class BaseEventModel(IBastionModel):
    """
    Base event model for recording events that occurred during a run.

    Attributes:
        run_id (str): ID of the run associated with the event.
        kind (EventKind): Kind of the event, e.g., 'base', 'error', etc.
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
    kind: EventKind = Field(
        default=EventKind.BASE,
        description="Kind of the event, e.g., 'base', 'error', etc.",
    )
    message: str = Field(
        ...,
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

    def export(self) -> dict[str, Any]:
        """
        Export the event as a dictionary with serialized fields.
        """
        return {
            "id": self.id,
            "run_id": self.run_id,
            "kind": self.kind.value,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
