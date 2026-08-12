from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar
from pydantic import Field

from bastion._internal.clock import IBastionClock
from bastion._internal.model import IBastionModel

from bastion.domain.asset.base.base import BaseAssetModel
from bastion.domain.event.base.base import BaseEventModel
from bastion.domain.quality.base import BaseQualityModel


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseRunModel(IBastionModel):
    _id_prefix: ClassVar[str] = "run"
    _id_length: ClassVar[int] = 16

    assets: list[BaseAssetModel] = Field(default_factory=list)
    events: list[BaseEventModel] = Field(default_factory=list)
    qualities: list[BaseQualityModel] = Field(default_factory=list)

    status: RunStatus = Field(default=RunStatus.PENDING)
    created_at: datetime = Field(default_factory=IBastionClock.current)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)

    def start(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = IBastionClock.current()

    def succeed(self) -> None:
        self.status = RunStatus.SUCCEEDED
        self.finished_at = IBastionClock.current()

    def fail(self) -> None:
        self.status = RunStatus.FAILED
        self.finished_at = IBastionClock.current()

    def cancel(self) -> None:
        self.status = RunStatus.CANCELLED
        self.finished_at = IBastionClock.current()

    def export(self) -> dict[str, Any]:
        _assets_export = [asset.export() for asset in self.assets]
        _events_export = [event.export() for event in self.events]
        _qualities_export = [quality.export() for quality in self.qualities]
        _created_at = self.created_at.isoformat() if self.created_at else None
        _started_at = self.started_at.isoformat() if self.started_at else None
        _finished_at = self.finished_at.isoformat() if self.finished_at else None
        return {
            "id": self.id,
            "assets": _assets_export,
            "events": _events_export,
            "qualities": _qualities_export,
            "status": self.status.value,
            "created_at": _created_at,
            "started_at": _started_at,
            "finished_at": _finished_at,
        }
