from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class MoneyMarketRatesMonthDataset(RBADataset):
    """
    RBA Interest Rates and Yields - Money Market (table F1.1) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "money_market_rates_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        table_no (str):
            RBA statistical table number, fixed to "f1.1"

    """

    name: ClassVar[str] = "money_market_rates_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Dataset for RBA Interest Rates and Yields - Money Market. "
        "Monthly cash rate, bank accepted bills and OIS rates."
    )
    table_no: ClassVar[str] = "f1.1"
