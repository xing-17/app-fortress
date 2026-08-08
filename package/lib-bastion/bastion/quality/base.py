from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel


from enum import StrEnum


class QualityStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

class BaseQuality(IBastionModel):
    _id_prefix: ClassVar[str] = "qual"
    _id_length: ClassVar[int] = 20
    run_id: str
    status: QualityStatus
    metrics: dict[str, Any] = Field(default_factory=dict) 
