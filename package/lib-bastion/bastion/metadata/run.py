from __future__ import annotations

import logging
from typing import Any, Protocol

from bastion._internal.object import IBastionObject
from bastion.domain.run.base import BaseRunModel, RunStatus
from bastion.metadata.event import Event
from bastion.metadata.quality import Quality

logger = logging.getLogger(__name__)

RunModel = BaseRunModel


class IRunLike(Protocol):
    domain: RunModel
    id: str
    status: RunStatus
    bridge_name: str
    name: str
    created_at: str | None
    started_at: str | None
    finished_at: str | None

    @classmethod
    def from_any(cls, data: dict[str, str | dict]) -> IRunLike: ...

    def event(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def add_event(
        self,
        event: Event,
    ) -> None: ...

    def start(self) -> None: ...

    def succeed(self) -> None: ...

    def fail(self) -> None: ...

    def cancel(self) -> None: ...

    def export(self) -> dict[str, Any]: ...


class Run(
    IBastionObject,
    IRunLike,
):
    """
    Wrapper for run metadata that tracks bridge execution with events and quality checks.

    Attributes:
        domain (RunModel): The underlying run domain model.
        events (list[Event]): List of events associated with this run.
        qualities (list[Quality]): List of quality checks associated with this run.

    Methods:
        from_any(data: Run | dict[str, list, dict]) -> Run: Create Run from dict or Run instance.
        id: Get the run ID.
        status: Get the current run status.
        _sha256_key: Get the SHA256 hash key for uniqueness.
        add_event(event: Event) -> None: Add an event to the run.
        add_quality(quality: Quality) -> None: Add a quality check to the run.
        start() -> None: Mark the run as started.
        succeed() -> None: Mark the run as succeeded.
        fail() -> None: Mark the run as failed.
        cancel() -> None: Mark the run as cancelled.
        export() -> dict[str, Any]: Export run data as a dictionary.

    Example:
        ```python
        run = Run(bridge_name="my_bridge")
        run.start()
        run.add_event(Event(run_id=run.id, message="Processing started"))
        run.succeed()
        exported = run.export()
        ```
    """

    @classmethod
    def from_any(
        cls,
        data: Run | dict[str, list, dict],
    ) -> Run:
        if isinstance(data, Run):
            return data
        try:
            return cls(
                bridge_name=data["bridge_name"],
                id=data.get("id"),
                name=data.get("name"),
                status=data.get("status"),
                created_at=data.get("created_at"),
                started_at=data.get("started_at"),
                finished_at=data.get("finished_at"),
                events=[Event.from_any(e) for e in data.get("events", [])],
                qualities=[Quality.from_any(q) for q in data.get("qualities", [])],
            )
        except Exception as e:
            raise ValueError(f"Can not create Run: {e}") from e

    def __init__(
        self,
        bridge_name: str,
        name: str | None = None,
        id: str | None = None,
        status: str | RunStatus | None = None,
        created_at: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        events: list[Event] | None = None,
        qualities: list[Quality] | None = None,
    ):
        super().__init__()
        self.domain = RunModel.from_any(
            {
                "id": id,
                "name": name,
                "bridge_name": bridge_name,
                "status": status or RunStatus.PENDING,
                "created_at": created_at,
                "started_at": started_at,
                "finished_at": finished_at,
            }
        )
        self.events: list[Event] = events or []
        self.qualities: list[Quality] = qualities or []

    @property
    def id(self) -> str:
        return self.domain.id

    @property
    def bridge_name(self) -> str:
        return self.domain.bridge_name

    @property
    def status(self) -> RunStatus:
        return self.domain.status

    @property
    def _sha256_key(self) -> str:
        return self.domain._sha256_key

    @property
    def name(self) -> str:
        if not self.domain.name:
            return f"{self.id}"
        return self.domain.name

    @property
    def created_at(self) -> str:
        return self.domain.created_at

    @property
    def started_at(self) -> str | None:
        return self.domain.started_at

    @property
    def finished_at(self) -> str | None:
        return self.domain.finished_at

    def event(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = Event(
            run_id=self.id,
            message=message,
            metadata=metadata or {},
        )
        self.add_event(event)

    def add_event(
        self,
        event: Event,
    ) -> None:
        _seen_hashes = {e._sha256_key for e in self.events}
        if event._sha256_key in _seen_hashes:
            logger.warning(f"Event '{event.id}' already exists.")
        else:
            self.events.append(event)
            logger.debug(f"Added event '{event.id}' to run '{self.id}'.")

    def quality(
        self,
        kind: str | None = None,
        passed: bool | None = None,
        description: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
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
        _seen_hashes = {q._sha256_key for q in self.qualities}
        if quality._sha256_key in _seen_hashes:
            logger.warning(f"Quality '{quality.id}' already exists.")
        else:
            self.qualities.append(quality)
            logger.debug(f"Added quality '{quality.id}' to run '{self.id}'.")

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

    def export(self) -> dict[str, Any]:
        return {
            **self.domain.export(),
            "events": [event.export() for event in self.events],
            "qualities": [quality.export() for quality in self.qualities],
        }
