from __future__ import annotations

from enum import Enum


class BaseInstanceStatus(str, Enum):
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


class BaseInstanceContext:
    def __init__(
        self,
        instance_name: str,
        instance_id: str,
        status: BaseInstanceStatus,
    ):
        self.instance_id = instance_id
        self.status = status


class BaseInstance:
    def __init__(
        self,
        instance_id: str,
    ):
        self.instance_id = instance_id

    def ping(self) -> bool:
        raise NotImplementedError("Ping method must be implemented by subclasses.")

    def start(self):
        raise NotImplementedError("Start method must be implemented by subclasses.")

    def stop(self):
        raise NotImplementedError("Stop method must be implemented by subclasses.")

    def restart(self):
        self.stop()
        self.start()
