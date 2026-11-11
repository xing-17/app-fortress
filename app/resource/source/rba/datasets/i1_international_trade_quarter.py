from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class I1InternationalTradeQuarterDataset(RBADataset):
    """
    RBA International Trade (table I1) - Quarterly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "i1_international_trade_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "i1"

    """

    name: ClassVar[str] = "i1_international_trade_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "International Trade and Balance of Payments (RBA I1), quarterly, from 1959, seasonally adjusted. "
        "Chain volume exports and imports ($ million): goods and services, services, and by category "
        "(rural, resource, coal, metal ores and minerals, other mineral fuels, manufactures; "
        "consumption, intermediate and capital goods imports), "
        "year-ended volume growth and share of nominal GDP (per cent), "
        "plus trade balance and current account balance as per cent of nominal GDP. "
        "Category detail starts in 1974 or 1985, no price or nominal $ values."
    )
    table_no: ClassVar[str] = "i1"
