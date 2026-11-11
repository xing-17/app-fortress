from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F12ExchangeRatesUsDollarMonthDataset(RBADataset):
    """
    RBA US Dollar Exchange Rates (table F12) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f12_exchange_rates_us_dollar_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f12"

    """

    name: ClassVar[str] = "f12_exchange_rates_us_dollar_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "US Dollar Exchange Rates (RBA F12), monthly, from 1980, original, month-end. "
        "Other major currencies quoted per 1 US dollar (Canadian dollar, euro, Japanese yen, pound sterling, Swiss franc), "
        "plus the US dollar major currency trade-weighted index (March 1973 = 100). "
        "Cross rates of the USD, not AUD rates, see f11 datasets for AUD."
    )
    table_no: ClassVar[str] = "f12"
