from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def from_any(
        cls,
        value: str | RunStatus,
    ) -> RunStatus:
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid RunStatus value: {value}")


class BaseRunModel(IBastionModel):
    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "run"
    _id_length: ClassVar[int] = 16
    bridge_name: str = Field(
        ...,
        description="Name of the bridge associated with the run.",
    )
    status: RunStatus = Field(
        RunStatus.PENDING,
        description="Current status of the run.",
    )
    # created_at is set at base model
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the run was created.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Datetime when the run started.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Datetime when the run finished.",
    )

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

    def export(self) -> dict[str, Any]:
        _created_at = self.created_at.isoformat() if self.created_at else None
        _started_at = self.started_at.isoformat() if self.started_at else None
        _finished_at = self.finished_at.isoformat() if self.finished_at else None
        return {
            "id": self.id,
            "bridge_name": self.bridge_name,
            "status": self.status.value,
            "created_at": _created_at,
            "started_at": _started_at,
            "finished_at": _finished_at,
        }
