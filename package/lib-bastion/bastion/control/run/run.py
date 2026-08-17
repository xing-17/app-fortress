from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bastion._internal.object import IBastionObject
from bastion.control.run.event import Event, EventModel, IEventLike
from bastion.control.run.quality import IQualityLike, Quality, QualityModel
from bastion.domain.run.base import BaseRunModel, RunStatus

logger = logging.getLogger(__name__)


RunModel = BaseRunModel


@runtime_checkable
class IRunLike(Protocol):
    # IBastionObject attributes
    domain: RunModel

    # run attributes
    id: str
    status: RunStatus
    bridge_name: str
    name: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    events: list[IEventLike]
    qualities: list[IQualityLike]

    # additional attributes for integrity
    logic_name: str | None
    sha256: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IRunLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: RunModel,
    ) -> IRunLike: ...

    def list_events(self) -> list[IEventLike]: ...

    def list_qualities(self) -> list[IQualityLike]: ...

    def event(
        self,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def quality(
        self,
        kind: str | None = None,
        passed: bool | None = None,
        description: str | None = None,
        metrics: dict[str, Any] | None = None,
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

    def __init__(
        self,
        bridge_name: str,
        name: str | None = None,
        id: str | None = None,
        status: str | RunStatus | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        events: list[Event] | None = None,
        qualities: list[Quality] | None = None,
    ):
        super().__init__(
            bridge_name=bridge_name,
            name=name,
            id=id,
            status=status,
            created_at=created_at,
            started_at=started_at,
            finished_at=finished_at,
            events=events or [],
            qualities=qualities or [],
        )

    def list_events(self) -> list[Event]:
        return self.events

    def list_qualities(self) -> list[Quality]:
        return self.qualities

    def event(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add new event to run

        Args:
            message (str): message of the event
            metadata (dict[str, Any] | None, optional): event metadata. Defaults to None.
        """
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
        _seens = {e.sha256 for e in self.events}
        if event.sha256 in _seens:
            logger.warning(f"Event '{event.id}' already exists.")
        else:
            _new_domain: EventModel = event.domain
            self.domain.events.append(_new_domain)
            logger.debug(f"Added event '{event.id}' OK.")

    def quality(
        self,
        kind: str | None = None,
        passed: bool | None = None,
        description: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """
        Add new quality summary to run

        Args:
            kind (str | None, optional): quality kind string. Defaults to None.
            passed (bool | None, optional): quality is passed. Defaults to None.
            description (str | None, optional): quality description. Defaults to None.
            metrics (dict[str, Any] | None, optional): quality metrics. Defaults to None.
        """
        quality = Quality(
            run_id=self.id,
            kind=kind,
            passed=passed,
            description=description,
            metrics=metrics,
        )
        self.add_quality(quality)

    def add_quality(
        self,
        quality: Quality,
    ) -> None:
        _seens = {q.sha256 for q in self.qualities}
        if quality.sha256 in _seens:
            logger.warning(f"Quality '{quality.id}' already exists.")
        else:
            _new_domain: QualityModel = quality.domain
            self.domain.qualities.append(_new_domain)
            logger.debug(f"Added quality '{quality.id}' OK.")

    def _on_start(self) -> None:
        pass

    def start(self) -> None:
        self._on_start()
        self.domain.start()

    def _on_succeed(self) -> None:
        pass

    def succeed(self) -> None:
        self._on_succeed()
        self.domain.succeed()

    def _on_fail(self) -> None:
        pass

    def fail(self) -> None:
        self._on_fail()
        self.domain.fail()

    def _on_cancel(self) -> None:
        pass

    def cancel(self) -> None:
        self._on_cancel()
        self.domain.cancel()
