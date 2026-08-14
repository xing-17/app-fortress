from __future__ import annotations

from typing import Protocol

from bastion._internal.object import IBastionObject
from bastion.domain.event.base import BaseEventModel

EventModel = BaseEventModel

class IEventLike(Protocol):
    domain: EventModel

    def export(self) -> dict[str, str | dict]: ...

class Event(
    IBastionObject,
):
    def __init__(
        self,
        run_id: str,
        message: str,
        metadata: dict[str, str] | None = None,
    ):
        super().__init__()
        self.domain = EventModel(
            run_id=run_id,
            message=message,
            metadata=metadata or {},
        )

    def export(self) -> dict[str, str | dict[str, str]]:
        return {
            "domain": self.domain.export(),
        }
