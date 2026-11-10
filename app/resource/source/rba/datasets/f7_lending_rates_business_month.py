from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F7LendingRatesBusinessMonthDataset(RBADataset):
    """
    RBA Business Lending Rates (table F7) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f7_lending_rates_business_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f7"

    """

    name: ClassVar[str] = "f7_lending_rates_business_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Business Lending Rates (RBA F7), monthly, from Jul 2019, per cent per annum. "
        "Average rates on new loans funded in the month and on outstanding loans, "
        "by business size (small, medium, large) and fixed or variable rate, "
        "including residentially secured small business loans."
    )
    table_no: ClassVar[str] = "f7"
