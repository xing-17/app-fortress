from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source._common._dataset import BaseDataset


class BrokenDataset(BaseDataset):
    # extract/transform/write left unimplemented on purpose
    provider: ClassVar[SourceProvider] = SourceProvider.TUSHARE
    name: ClassVar[str] = "broken"
    frequency: ClassVar[FrequencyOption] = FrequencyOption.DAY
