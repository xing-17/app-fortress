from __future__ import annotations

from enum import StrEnum


class ComputeStatus(StrEnum):
    """
    Enumeration of the status of a submitted compute job

    Values:
    ----------
        STARTED: The job is still executing
        COMPLETED: The job finished without raising
        FAILED: The job raised or its process died
        CANCELLED: The job was cancelled
        UNKNOWN: The runtime cannot report the status, the Run record in the store is the truth

    """

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
