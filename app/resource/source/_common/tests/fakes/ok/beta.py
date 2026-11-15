from __future__ import annotations

from typing import ClassVar

from app.internal.model.definition.desc import ColumnDesc
from app.resource.source._common.tests.fakes.base import FakeDataset


class BetaDataset(FakeDataset):
    name: ClassVar[str] = "beta"
    partitions: ClassVar[list[str]] = ["year"]
    column_descs: ClassVar[list[ColumnDesc]] = [
        ColumnDesc(name="a", description="First column", unit="kg"),
        ColumnDesc(name="b", description="Second column"),
    ]
