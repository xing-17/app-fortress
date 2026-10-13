from __future__ import annotations

from typing import ClassVar

from app.resource.source._common.tests.fakes.base import FakeDataset


class BetaDataset(FakeDataset):
    name: ClassVar[str] = "beta"
    partitions: ClassVar[list[str]] = ["year"]
