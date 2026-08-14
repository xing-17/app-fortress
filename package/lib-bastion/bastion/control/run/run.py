from __future__ import annotations

from typing import Protocol

from bastion._internal.object import IBastionObject
from bastion.domain.run.base import BaseRunModel

RunModel = BaseRunModel


class IRunLike(Protocol):
    domain: RunModel

    def _on_start(self) -> None: ...

    def start(self) -> None:
        self._on_start()
        self.domain.start()

    def _on_succeed(self) -> None: ...

    def succeed(self) -> None:
        """Mark the run as succeeded."""
        self._on_succeed()
        self.domain.succeed()

    def _on_fail(self) -> None: ...

    def fail(self) -> None:
        """Mark the run as failed."""
        self._on_fail()
        self.domain.fail()

    def _on_cancel(self) -> None: ...

    def cancel(self) -> None:
        """Cancel the run."""
        self._on_cancel()
        self.domain.cancel()
        
    def export(self) -> dict[str, str | dict[str, str]]: ...


class Run(
    IRunLike,
    IBastionObject,
):
    def __init__(
        self,
        bridge_name: str,
    ):
        super().__init__()
        self.domain = RunModel(
            bridge_name=bridge_name,
        )

    def _on_start(self) -> None:
        pass

    def _on_succeed(self) -> None:
        pass

    def _on_fail(self) -> None:
        pass

    def _on_cancel(self) -> None:
        pass

    def export(self) -> dict[str, str | dict]:
        return {
            "domain": self.domain.export(),
        }
    