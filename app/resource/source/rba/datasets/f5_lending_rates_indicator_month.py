from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F5LendingRatesIndicatorMonthDataset(RBADataset):
    """
    RBA Indicator Lending Rates (table F5) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f5_lending_rates_indicator_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f5"

    """

    name: ClassVar[str] = "f5_lending_rates_indicator_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Indicator Lending Rates (RBA F5), monthly, from 1959, per cent per annum. "
        "Advertised benchmark rates: bank and mortgage manager housing loans (standard, discounted, fixed, "
        "owner-occupier and investor), securitised housing average rates, small and large business, "
        "personal loans (term, credit cards, margin, home equity). "
        "Benchmark rates, not actual loan flows, see F6, F7 and F8 datasets for those."
    )
    table_no: ClassVar[str] = "f5"
