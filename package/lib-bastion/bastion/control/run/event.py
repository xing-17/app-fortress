from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion.domain.event import EventModel


@runtime_checkable
class IEventLike(Protocol):
    id: str
    run_id: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime | None
    tags: dict[str, str] | None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IEventLike: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...


Event = EventModel
