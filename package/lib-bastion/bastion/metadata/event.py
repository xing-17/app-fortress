from __future__ import annotations

from typing import Any

from bastion._internal.object import IBastionObject
from bastion.domain.event.base import BaseEventModel

EventModel = BaseEventModel


class Event(IBastionObject):
    """
    Wrapper for event metadata associated with a run.

    Attributes:
        domain (EventModel): The underlying event domain model.

    Methods:
        from_any(data: Event | dict[str, str | dict]) -> Event: Create Event from dict or Event instance.
        id: Get the event ID.
        run_id: Get the run ID associated with this event.
        _sha256_key: Get the SHA256 hash key for uniqueness.
        export() -> dict[str, Any]: Export event data as a dictionary.

    Example:
        ```python
        event = Event(run_id="run-123", message="Task started")
        exported = event.export()
        ```
    """

    @classmethod
    def from_any(
        cls,
        data: Event | dict[str, str | dict],
    ) -> Event:
        if isinstance(data, Event):
            return data
        try:
            return cls(
                id=data.get("id", None),
                run_id=data["run_id"],
                created_at=data.get("created_at", None),
                message=data.get("message", None),
                metadata=data.get("metadata", None),
            )
        except Exception as e:
            raise ValueError(f"Invalid data for Event: {data}") from e

    def __init__(
        self,
        run_id: str,
        id: str | None = None,
        created_at: str | None = None,
        message: str | None = None,
        metadata: dict[str, str] | None = None,
    ):
        super().__init__()
        self.domain: EventModel = EventModel.from_any(
            {
                "id": id,
                "run_id": run_id,
                "message": message,
                "created_at": created_at,
                "metadata": metadata,
            }
        )

    @property
    def id(self) -> str:
        return self.domain.id

    @property
    def run_id(self) -> str:
        return self.domain.run_id

    @property
    def _sha256_key(self) -> str:
        return self.domain._sha256_key

    def export(self) -> dict[str, Any]:
        return {
            **self.domain.export(),
        }
