from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion._internal.object import IBastionObject
from bastion.domain.event.base import BaseEventModel

EventModel = BaseEventModel


@runtime_checkable
class IEventLike(Protocol):
    # IBastionObject attributes
    domain: BaseEventModel

    # event attributes
    id: str
    run_id: str
    message: str
    metadata: dict[str, Any]
    created_at: str | None

    # additional attributes for integrity
    logic_name: str | None
    sha256: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IEventLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: EventModel,
    ) -> IEventLike: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> str: ...


class Event(
    IBastionObject,
    IEventLike,
):
    _domain_class = EventModel

    def __init__(
        self,
        run_id: str,
        id: str | None = None,
        message: str | None = None,
        created_at: datetime | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            run_id=run_id,
            id=id,
            message=message,
            created_at=created_at,
            metadata=metadata,
        )
