from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F11_1ExchangeRatesRecentDayDataset(RBADataset):
    """
    RBA Recent Exchange Rates (table F11.1) - Daily, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f11_1_exchange_rates_recent_day"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.DAY
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f11.1"

    """

    name: ClassVar[str] = "f11_1_exchange_rates_recent_day"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.DAY
    description: ClassVar[str] = (
        "Exchange Rates - Daily, 2023 to Current (RBA F11.1), daily, from Jan 2023. "
        "Indicative AUD exchange rates: foreign currency units per 1 AUD (e.g. AUD/USD, AUD/EUR, AUD/JPY, AUD/CNY, "
        "also GBP, NZD, SGD, HKD, KRW, INR and other Asia-Pacific currencies, SDR), "
        "plus the Australian dollar trade-weighted index (index). "
        "Daily observations, one series per currency. Older daily and monthly history is in f11_exchange_rates_historical_month."
    )
    table_no: ClassVar[str] = "f11.1"
