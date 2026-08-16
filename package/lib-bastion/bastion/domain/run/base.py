from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class RunStatus(StrEnum):
    """
    Run status enumeration for tracking execution states.

    Attributes:
        PENDING (str): Run is pending execution.
        RUNNING (str): Run is currently executing.
        SUCCEEDED (str): Run completed successfully.
        FAILED (str): Run failed with an error.
        CANCELLED (str): Run was cancelled.

    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseRunModel(IBastionModel):
    """
    Base run model for tracking bridge execution lifecycle and managing run state transitions.

    Attributes:
        id (str): Unique identifier with 'run' prefix (inherited from IBastionModel).
        bridge_name (str): Name of the bridge associated with the run.
        name (str | None): Optional name for the run.
        status (RunStatus): Current status of the run (pending, running, succeeded, failed, cancelled).
        created_at (datetime): Datetime when the run was created.
        started_at (datetime | None): Datetime when the run started.
        finished_at (datetime | None): Datetime when the run finished.

    Methods:
        from_any(value): Convert dict or instance to run model (inherited).
        start(): Mark the run as started and set started_at timestamp.
        succeed(): Mark the run as succeeded and set finished_at timestamp.
        fail(): Mark the run as failed and set finished_at timestamp.
        cancel(): Mark the run as cancelled and set finished_at timestamp.
        export(): Export the run as a dictionary with serialized fields.
        describe(): Export run as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).
        logic_name: Get logical name of the run (inherited property).
        sha256: Get SHA256 hash of the run (inherited property).

    Example:
        ```python
        run = BaseRunModel(bridge_name="my_bridge")
        print(run.id)  # run-a1b2c3d4e5f6
        run.start()
        # ... execute bridge logic ...
        run.succeed()
        exported = run.export()
        ```
    """

    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "run"
    _id_length: ClassVar[int] = 16
    bridge_name: str = Field(
        ...,
        description="Name of the bridge associated with the run.",
    )
    name: str | None = Field(
        default=None,
        description="Optional name for the run.",
    )
    status: RunStatus = Field(
        RunStatus.PENDING,
        description="Current status of the run.",
    )
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

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_required_datetime(cls, v: Any) -> Any:
        if v is None:
            return IBastionClock.current()  # None means "use factory default"
        if isinstance(v, str):
            return IBastionClock.from_iso(v)
        return v

    @field_validator("started_at", "finished_at", mode="before")
    @classmethod
    def _coerce_optional_datetime(cls, v: Any) -> Any:
        if isinstance(v, str):
            return IBastionClock.from_iso(v)
        return v

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
            "name": self.name,
            "bridge_name": self.bridge_name,
            "status": self.status.value,
            "created_at": _created_at,
            "started_at": _started_at,
            "finished_at": _finished_at,
        }
