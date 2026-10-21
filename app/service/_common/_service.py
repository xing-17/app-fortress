from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from app.internal.constant.servicekind import ServiceKind
from app.internal.constant.servicestate import ServiceState
from app.internal.logstream import LogStream
from app.resource._global.logstreams import GlobalLogStreams
from app.setting.service import AbstractServiceSetting

# Type variable for service setting
S = TypeVar("S", bound=AbstractServiceSetting)


class BaseService(ABC, Generic[S]):
    """
    Base service class for fortress, owns the lifecycle state machine.

    CREATED/STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED
    STARTING/STOPPING -> FAILED when the hook raises

    Attributes:
        kind (ServiceKind): Service kind, fixed by each concrete service
        setting (S): Service setting
        log (LogStream): Service log stream, from setting.log
        state (ServiceState): Current lifecycle state

    Methods:
        start() -> None:
            Start the service, no-op when already RUNNING.

        stop() -> None:
            Stop the service, no-op when CREATED or STOPPED.

        health() -> dict:
            Return the kind and state, subclasses may extend it.

    """

    kind: ClassVar[ServiceKind]

    def __init__(
        self,
        setting: S,
    ) -> None:
        if setting.kind != self.kind:
            _type_name: str = type(self).__name__
            _setting_kind: str = str(setting.kind)
            raise ValueError(f"{_type_name} requires a {self.kind} setting, got {_setting_kind}")

        self._setting: S = setting
        self._state: ServiceState = ServiceState.CREATED
        self._lock = threading.RLock()
        self._log: LogStream = GlobalLogStreams.resolve(
            value=setting.log,
            default=LogStream(name=str(self.kind), tags={"service": str(self.kind)}),
        )

    @property
    def is_running(self) -> bool:
        return self._state == ServiceState.RUNNING

    @property
    def setting(self) -> S:
        return self._setting

    @property
    def log(self) -> LogStream:
        return self._log

    @property
    def state(self) -> ServiceState:
        return self._state

    @abstractmethod
    def _start(self) -> None:
        """Acquire resources and begin serving."""

    @abstractmethod
    def _stop(self) -> None:
        """Release resources, must tolerate a partially started service."""

    def _transition(
        self,
        new_state: ServiceState,
    ) -> None:
        _prev, self._state = self._state, new_state
        self._log.info(
            f"{self.kind}: {_prev} -> {new_state}",
            metadata={
                "from": str(_prev),
                "to": str(new_state),
            },
        )

    def start(self) -> None:
        with self._lock:
            if self._state == ServiceState.RUNNING:
                return
            if self._state not in (
                ServiceState.CREATED,
                ServiceState.STOPPED,
            ):
                raise RuntimeError(f"{self.kind} cannot start from state {self._state}")

            self._transition(ServiceState.STARTING)
            try:
                self._start()
            except BaseException:
                self._log.exception(f"{self.kind}: start failed")
                self._transition(ServiceState.FAILED)
                raise
            self._transition(ServiceState.RUNNING)

    def stop(self) -> None:
        with self._lock:
            if self._state in (
                ServiceState.CREATED,
                ServiceState.STOPPED,
            ):
                return
            if self._state in (
                ServiceState.STARTING,
                ServiceState.STOPPING,
            ):
                raise RuntimeError(f"{self.kind} cannot stop from state {self._state}")

            self._transition(ServiceState.STOPPING)
            try:
                self._stop()
            except BaseException:
                self._log.exception(f"{self.kind}: stop failed")
                self._transition(ServiceState.FAILED)
                raise
            self._transition(ServiceState.STOPPED)

    def health(self) -> dict:
        return {
            "kind": str(self.kind),
            "state": str(self._state),
            "is_running": self.is_running,
        }
