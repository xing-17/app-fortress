from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseEventModel(IBastionModel):
    # Event SHOULD be immutable
    _id_prefix: ClassVar[str] = "event"
    _id_length: ClassVar[int] = 16

    message: str
    created_at: datetime = Field(default_factory=IBastionClock.current)
    metadata: dict[str, Any] = Field(default_factory=dict)
