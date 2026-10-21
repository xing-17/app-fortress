from __future__ import annotations

from enum import StrEnum


class ServiceState(StrEnum):
    """
    Enumeration of the lifecycle state of a service

    Values:
    ----------
        CREATED: Constructed, never started
        STARTING: start() is running
        RUNNING: Started successfully
        STOPPING: stop() is running
        STOPPED: Stopped, can be started again
        FAILED: start() or stop() raised, stop() is still allowed for cleanup

    """

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
