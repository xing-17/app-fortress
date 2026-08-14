from __future__ import annotations

from typing import Protocol

from bastion.control.run.run import IRunLike
from bastion.domain.run.base import BaseRunModel
from bastion.infra.store.base.base import IStoreLike

RunModel = BaseRunModel


class IComputeLike(Protocol):
    domain: RunModel

    def execute(
        self,
        run: IRunLike,
        store: IStoreLike,
        params: dict[str, str] | None = None,
    ) -> None:
        """Execute the compute resource with the given parameters."""
        ...
