from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseAgentModel(IBastionModel):
    _id_prefix: ClassVar[str] = "agent"
    _id_length: ClassVar[int] = 12

    name: str = Field(
        ...,
        description="Name of the agent",
    )
    kind: str = Field(
        ...,
        description="Kind of the agent, e.g., 'docker', 'kubernetes', etc.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the agent",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for the agent",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the agent",
    )

    def export(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "config": self.config,
            "tags": self.tags,
        }
