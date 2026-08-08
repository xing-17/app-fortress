from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import Field
from typing import Any

from bastion._internal.model import IBastionModel

class PipelineLike(Protocol):
    id: str
    name: str
    asset_id: str
    description: str | None
    metadata: dict[str, Any]
    tags: dict[str, str]

class BasePipeline(IBastionModel):
    _id_prefix: ClassVar[str] = "pipe"
    _id_length: ClassVar[int] = 12
    name: str
    asset_id: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
