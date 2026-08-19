from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class EventModel(IBastionModel):
    """
    Base EventModel model for recording events that occurred during a run execution.

    Attributes:
        id (str): Unique identifier with 'event' prefix (inherited from IBastionModel).
        run_id (str): ID of the run associated with the EventModel.
        message (str | None): Message content of the event.
        created_at (datetime): Datetime when the event was created.
        metadata (dict[str, Any]): Additional metadata related to the event.
        tags (dict[str, str]): Tags associated with the event.
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        from_any(value): Convert dict or instance to EventModel model (inherited).
        export(): Export the event as a dictionary with serialized fields.
        describe(): Export event as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    Example:
        ```python
        event = EventModel(
            run_id="run-123abc",
            message="Task completed successfully",
            metadata={"duration_ms": 1500}
        )
        exported = event.export()
        ```
    """

    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "event"
    _id_length: ClassVar[int] = 16
    run_id: str = Field(
        ...,
        description="ID of the run associated with the EventModel.",
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
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the event.",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_required_datetime(cls, v: Any) -> Any:
        if v is None:
            return IBastionClock.current()
        if isinstance(v, str):
            return IBastionClock.from_iso(v)
        return v
