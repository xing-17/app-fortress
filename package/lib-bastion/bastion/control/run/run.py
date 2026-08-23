from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion._internal.clock import IBastionClock
from bastion._internal.object import IBastionObject
from bastion.control.run.event import Event, IEventLike
from bastion.domain.run import RunModel, RunStatus


@runtime_checkable
class IRunLike(Protocol):
    # IBastionObject attributes
    domain: RunModel

    # run attributes
    compute_name: str
    id: str
    name: str | None
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    events: list[IEventLike]

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IRunLike: ...

    def list_events(self) -> list[IEventLike]: ...

    def event(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def start(self) -> None: ...

    def succeed(self) -> None: ...

    def fail(self) -> None: ...

    def cancel(self) -> None: ...

    def export(self) -> dict[str, Any]: ...

    def describe(self) -> dict[str, Any]: ...


class Run(
    IBastionObject,
    IRunLike,
):
    _domain_class: type[RunModel] = RunModel

    def list_events(self) -> list[Event]:
        return self.domain.events

    def event(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        new = Event(
            run_id=self.id,
            message=message,
            metadata=metadata,
        )
        self.add_event(new)

    def add_event(
        self,
        event: IEventLike,
    ) -> None:
        self.domain.events.append(event)

    def start(self) -> None:
        self.domain.status = RunStatus.RUNNING
        self.domain.started_at = IBastionClock.current()

    def succeed(self) -> None:
        self.domain.status = RunStatus.SUCCEEDED
        self.domain.finished_at = IBastionClock.current()

    def fail(self) -> None:
        self.domain.status = RunStatus.FAILED
        self.domain.finished_at = IBastionClock.current()

    def cancel(self) -> None:
        self.domain.status = RunStatus.CANCELLED
        self.domain.finished_at = IBastionClock.current()
