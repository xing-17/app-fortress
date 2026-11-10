from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F1_1MoneyMarketRatesMonthDataset(RBADataset):
    """
    RBA Interest Rates and Yields - Money Market (table F1.1) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f1_1_money_market_rates_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f1.1"

    """

    name: ClassVar[str] = "f1_1_money_market_rates_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Interest Rates and Yields - Money Market - Monthly (RBA F1.1), monthly averages, from 1969. "
        "Cash rate target, interbank overnight cash rate (with highest and lowest), "
        "1, 3 and 6 month bank accepted bills and NCDs, treasury notes and OIS, per cent per annum, "
        "plus overnight cash market volume ($m) and number of transactions. "
        "Monthly averages hide the exact policy change dates, daily data is RBA F1."
    )
    table_no: ClassVar[str] = "f1.1"
