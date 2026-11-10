from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F8LendingRatesPersonalMonthDataset(RBADataset):
    """
    RBA Personal Lending Rates (table F8) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f8_lending_rates_personal_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f8"

    """

    name: ClassVar[str] = "f8_lending_rates_personal_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Personal Lending Rates (RBA F8), monthly, from Jul 2019, per cent per annum. "
        "Average rates on new loans funded in the month and on outstanding personal credit: "
        "fixed-term loans (fixed or variable), credit card balances incurring interest, "
        "other revolving credit, margin lending, finance leases."
    )
    table_no: ClassVar[str] = "f8"
