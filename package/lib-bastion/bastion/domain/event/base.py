from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


class BaseEventModel(IBastionModel):
    _id_enabled: ClassVar[bool] = True
    _id_prefix: ClassVar[str] = "event"
    _id_length: ClassVar[int] = 16

    run_id: str = Field(
        ...,
        description="ID of the run associated with the event.",
    )
    message: str = Field(
        ...,
        description="Message content of the event.",
    )
    created_at: datetime = Field(
        default_factory=IBastionClock.current,
        description="Datetime when the event was created.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata related to the event.",
    )
