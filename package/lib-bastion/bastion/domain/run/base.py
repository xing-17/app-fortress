from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field

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

    Methods:
        from_any(value): Convert string or RunStatus to RunStatus instance.

    Example:
        ```python
        status = RunStatus.PENDING
        status_from_str = RunStatus.from_any("running")
        ```
    """

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
        """
        Convert string or RunStatus instance to RunStatus.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid RunStatus value: {value}")


class BaseRunModel(IBastionModel):
    """
    Base run model for tracking bridge execution lifecycle.

    Attributes:
        bridge_name (str): Name of the bridge associated with the run.
        status (RunStatus): Current status of the run.
        created_at (datetime): Datetime when the run was created.
        started_at (datetime | None): Datetime when the run started.
        finished_at (datetime | None): Datetime when the run finished.

    Methods:
        start(): Mark the run as started and set started_at timestamp.
        succeed(): Mark the run as succeeded and set finished_at timestamp.
        fail(): Mark the run as failed and set finished_at timestamp.
        cancel(): Mark the run as cancelled and set finished_at timestamp.
        export(): Export the run as a dictionary with serialized fields.

    Example:
        ```python
        run = BaseRunModel(bridge_name="my_bridge")
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

    @classmethod
    def from_any(
        cls,
        value: dict | BaseRunModel,
    ) -> BaseRunModel:
        if isinstance(value, BaseRunModel):
            return value
        try:
            _attrs = {
                "id": value.get("id"),
                "bridge_name": value.get("bridge_name"),
                "status": RunStatus.from_any(value.get("status", RunStatus.PENDING)),
                "created_at": IBastionClock.from_iso(value.get("created_at")),
                "started_at": IBastionClock.from_iso(value.get("started_at")),
                "finished_at": IBastionClock.from_iso(value.get("finished_at")),
            }
            return cls(**_attrs)
        except Exception as e:
            raise ValueError(f"Cannot create {cls.__name__}: {e}") from e

    def start(self) -> None:
        """
        Mark the run as started and set started_at timestamp.
        """
        self.status = RunStatus.RUNNING
        self.started_at = IBastionClock.current()

    def succeed(self) -> None:
        """
        Mark the run as succeeded and set finished_at timestamp.
        """
        self.status = RunStatus.SUCCEEDED
        self.finished_at = IBastionClock.current()

    def fail(self) -> None:
        """
        Mark the run as failed and set finished_at timestamp.
        """
        self.status = RunStatus.FAILED
        self.finished_at = IBastionClock.current()

    def cancel(self) -> None:
        """
        Mark the run as cancelled and set finished_at timestamp.
        """
        self.status = RunStatus.CANCELLED
        self.finished_at = IBastionClock.current()

    def export(self) -> dict[str, Any]:
        """
        Export the run as a dictionary with serialized fields.
        """
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
