from __future__ import annotations

from typing import Any, ClassVar
from pydantic import Field

from bastion._internal.model import IBastionModel


class BaseQualityModel(IBastionModel):
    _id_prefix: ClassVar[str] = "qual"
    _id_length: ClassVar[int] = 20
    metrics: dict[str, Any] = Field(default_factory=dict)
