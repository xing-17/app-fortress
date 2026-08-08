from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Protocol, runtime_checkable

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@runtime_checkable
class RunLike(Protocol):
    id: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def succeed(self) -> None: ...

    @abstractmethod
    def fail(self) -> None: ...

    @abstractmethod
    def cancel(self) -> None: ...


class BaseRun(IBastionModel):
    _id_prefix: ClassVar[str] = "run"
    _id_length: ClassVar[int] = 16
    status: RunStatus = Field(default=RunStatus.PENDING)
    created_at: datetime = Field(default_factory=IBastionClock.current)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)

    def start(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = IBastionClock.current()

    def succeed(self) -> None:
        self.status = RunStatus.SUCCEEDED
        self.finished_at = IBastionClock.current()

    def fail(self) -> None:
        self.status = RunStatus.FAILED
        self.finished_at = IBastionClock.current()

    def cancel(self) -> None:
        self.status = RunStatus.CANCELLED
        self.finished_at = IBastionClock.current()
