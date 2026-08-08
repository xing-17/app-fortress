from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Protocol, runtime_checkable

from pydantic import Field

from bastion.run.base.base import RunLike
from bastion.pipeline.base.base import PipelineLike


@runtime_checkable
class RuntimeLike(Protocol):
    id: str

    @abstractmethod
    def execute(
        self,
        pipeline: PipelineLike,
        run: RunLike,
    ) -> None:
        ...
