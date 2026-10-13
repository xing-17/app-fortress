from __future__ import annotations

from typing import ClassVar

# Imported (not defined here) dataset classes must be ignored by discovery
from app.resource.source._common.tests.fakes.base import FakeDataset


class AlphaDataset(FakeDataset):
    name: ClassVar[str] = "alpha"
