from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F11ExchangeRatesHistoricalMonthDataset(RBADataset):
    """
    RBA Historical Exchange Rates (table F11) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f11_exchange_rates_historical_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f1"

    """

    name: ClassVar[str] = "f11_exchange_rates_historical_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Exchange Rates - Historical (RBA F11), monthly, from Jan 2010. "
        "Indicative month-end AUD exchange rates: foreign currency units per 1 AUD (e.g. AUD/USD, AUD/EUR, AUD/JPY, "
        "AUD/CNY, also GBP, CHF, CAD, NZD, SGD, HKD, KRW, INR, AED, SAR, ZAR, SEK and others, SDR), "
        "plus the Australian dollar trade-weighted index (index). "
        "Currency coverage is wider than f12 (which is quoted per US dollar), recent daily data is f11_1_exchange_rates_recent_day."
    )
    table_no: ClassVar[str] = "f11"
