from __future__ import annotations

from typing import Any, ClassVar, Self

from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.internal.util.clock import IClock
from app.internal.util.id import IID


class ComputeRun(IAbstractDomain):
    """
    Record of a single execution of a compute, persisted in the compute's store table keyed by `id`

    Lifecycle: STARTED -> COMPLETED | FAILED | CANCELLED, a terminal run never changes again.

    Args:
    ----------
        id (str):
            Run identifier, generated locally
        status (ComputeStatus):
            Last known status, STARTED until a terminal status is observed
        compute (str):
            Name of the compute that executed the run
        runtime (ComputeRuntime):
            Runtime of that compute
        payload (dict[str, Any]):
            JSON payload passed into the entrypoint
        external_id (str | None):
            Id assigned by the runtime, if any
        result (dict[str, Any]):
            JSON result of a completed run, empty otherwise
        error (str | None):
            Failure message of a failed run, None otherwise
        started_at (float | None):
            Start timestamp, in UTC, defaults to the creation time
        finished_at (float | None):
            Timestamp at which a terminal status was observed, in UTC

    Attributes:
    ----------
        is_finished (bool):
            Whether the run has reached a terminal status
        duration (float):
            Seconds from start to finish, or to now if still running

    Methods:
    ----------
        submit(external_id: str) -> None:
            Record the runtime's id, the status stays STARTED.
        fail(error: Exception | str | None = None) -> None:
            Mark the run as failed with the given error.
        cancel() -> None:
            Mark the run as cancelled.
        complete(result: dict[str, Any] | None = None) -> None:
            Mark the run as completed with the given result.

    Raises:
    ----------
        ValueError:
            When `fail`, `cancel` or `complete` is called on a finished run

    """

    _terminals: ClassVar[frozenset[ComputeStatus]] = frozenset(
        {
            ComputeStatus.COMPLETED,
            ComputeStatus.FAILED,
            ComputeStatus.CANCELLED,
        }
    )
    _transitions: ClassVar[dict[ComputeStatus, frozenset[ComputeStatus]]] = {
        ComputeStatus.STARTED: frozenset(
            {
                ComputeStatus.COMPLETED,
                ComputeStatus.FAILED,
                ComputeStatus.CANCELLED,
            }
        ),
    }

    id: str = Field(
        default_factory=lambda: IID.generate_id(prefix="run", length=16),
        description="[Optional] Run identifier",
        min_length=1,
    )
    status: ComputeStatus = Field(
        default=ComputeStatus.STARTED,
        description="[Optional] Last known status, defaults to STARTED",
    )
    compute: str = Field(
        ...,
        description="[Required] Name of the compute that executed the run",
    )
    runtime: ComputeRuntime = Field(
        ...,
        description="[Required] Runtime of the compute",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="[Optional] JSON payload passed into the entrypoint",
    )
    external_id: str | None = Field(
        default=None,
        description="[Optional] Id assigned by the runtime",
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="[Optional] JSON result of a completed run",
    )
    error: str | None = Field(
        default=None,
        description="[Optional] Failure message of a failed run",
    )
    started_at: float | None = Field(
        default=None,
        description="[Optional] Start timestamp, in UTC, defaults to the creation time",
    )
    finished_at: float | None = Field(
        default=None,
        description="[Optional] Terminal status timestamp, in UTC",
    )

    @model_validator(mode="after")
    def _derive_started_at(self) -> Self:
        if self.started_at is None:
            object.__setattr__(self, "started_at", self._current())
        return self

    @property
    def is_finished(self) -> bool:
        return self.status in self._terminals

    @property
    def duration(self) -> float:
        _start: float = self.started_at if self.started_at is not None else self._current()
        _end: float = self.finished_at if self.finished_at is not None else self._current()
        return _end - _start

    def _current(self) -> float:
        return IClock.current_timestamp(timezone="UTC")

    def _check_transition(
        self,
        new: ComputeStatus,
    ) -> None:
        _allowed: frozenset[ComputeStatus] = self._transitions.get(self.status, frozenset())
        if new not in _allowed:
            raise ValueError(f"Transit from '{self.status}' to '{new}' not allowed")

    def submit(
        self,
        external_id: str,
    ) -> None:
        self.finished_at = None
        self.error = None
        self.external_id = external_id

    def fail(
        self,
        error: Exception | str | None = None,
    ) -> None:
        self._check_transition(ComputeStatus.FAILED)
        self.status = ComputeStatus.FAILED
        self.finished_at = self._current()
        self.error = str(error or "Unknown error")

    def cancel(self) -> None:
        self._check_transition(ComputeStatus.CANCELLED)
        self.status = ComputeStatus.CANCELLED
        self.finished_at = self._current()
        self.error = None

    def complete(
        self,
        result: dict[str, Any] | None = None,
    ) -> None:
        self._check_transition(ComputeStatus.COMPLETED)
        self.status = ComputeStatus.COMPLETED
        self.finished_at = self._current()
        self.error = None
        self.result = result or {}
