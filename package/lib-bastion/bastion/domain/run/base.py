from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import Field, field_validator

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel
from bastion.domain.event.base import BaseEventModel
from bastion.domain.quality.base import BaseQualityModel


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
    Base model for tracking bridge execution runs throughout their lifecycle.

    This model provides a comprehensive framework for managing the execution state of bridge runs,
    including status transitions, timestamp tracking, and associated events and quality checks.
    Each run is uniquely identified and tracks its progression from creation through completion.

    Attributes:
        id (str): Unique identifier with 'run' prefix and 16-character suffix (auto-generated).
        bridge_name (str): Name of the bridge associated with this run instance.
        name (str | None): Optional human-readable name for the run.
        status (RunStatus): Current execution status - one of PENDING, RUNNING, SUCCEEDED, FAILED, or CANCELLED.
        created_at (datetime): UTC timestamp when the run was instantiated.
        started_at (datetime | None): UTC timestamp when the run began execution (set by start()).
        finished_at (datetime | None): UTC timestamp when the run completed (set by succeed(), fail(), or cancel()).
        events (list[BaseEventModel]): Collection of events that occurred during run execution.
        qualities (list[BaseQualityModel]): Collection of quality checks performed during the run.
        logic_name (str): Logical identifier combining bridge_name and optional name.
        sha256 (str): SHA256 hash of the run's canonical representation.

    Methods:
        start(): Transitions status to RUNNING and records started_at timestamp.
        succeed(): Transitions status to SUCCEEDED and records finished_at timestamp.
        fail(): Transitions status to FAILED and records finished_at timestamp.
        cancel(): Transitions status to CANCELLED and records finished_at timestamp.
        from_any(value): Create instance from dict or existing model object.
        export(): Serialize run to dictionary with ISO-formatted datetimes.
        describe(): Serialize run to formatted JSON string.
        clone(**updates): Create deep copy of run with optional field updates.

    Example:
        ```python
        # Create and execute a run
        run = BaseRunModel(bridge_name="data_pipeline", name="daily_sync")
        print(f"Run ID: {run.id}")  # Run ID: run-a1b2c3d4e5f6789a
        print(f"Status: {run.status}")  # Status: pending

        run.start()
        # ... execute bridge logic ...

        try:
            # ... bridge operations ...
            run.succeed()
        except Exception:
            run.fail()

        # Export for persistence or API response
        data = run.export()
        print(f"Duration: {run.finished_at - run.started_at}")
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
    events: list[BaseEventModel] = Field(
        default_factory=list,
        description="List of events associated with the run.",
    )
    qualities: list[BaseQualityModel] = Field(
        default_factory=list,
        description="List of quality checks associated with the run.",
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
