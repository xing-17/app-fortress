from __future__ import annotations

from enum import StrEnum


class ComputeStatus(StrEnum):
    """
    Enumeration of the venue-level status of a submitted compute job

    Values:
    ----------
        NOT_STARTED: The job has not started yet
        STARTED: The job is still executing
        SUCCEEDED: The job finished without raising
        FAILED: The job raised or its process died
        CANCELLED: The job was cancelled
        UNKNOWN: The runtime cannot report the status, the Run record in the store is the truth

    """

    NOT_STARTED = "not_started"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
