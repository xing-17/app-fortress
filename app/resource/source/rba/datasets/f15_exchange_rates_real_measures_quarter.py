from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F15ExchangeRatesRealMeasuresQuarterDataset(RBADataset):
    """
    RBA Real Exchange Rates (table F15) - Quarterly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f15_exchange_rates_real_measures_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f15"

    """

    name: ClassVar[str] = "f15_exchange_rates_real_measures_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Real Exchange Rate Measures (RBA F15), quarterly, from 1970, index (March 1995 = 100), original, quarter-average. "
        "Australian dollar real exchange rate indices adjusted for relative consumer prices: "
        "trade-weighted, export-weighted and import-weighted. "
        "Aggregate indices only, no bilateral currency rates, see f11 and f12 for nominal rates."
    )
    table_no: ClassVar[str] = "f15"
