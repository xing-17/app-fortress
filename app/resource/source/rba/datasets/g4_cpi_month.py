from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class G4CPIMonthDataset(RBADataset):
    """
    RBA Consumer Price Inflation - Monthly Collection (table G4), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "g4_cpi_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "g4"

    """

    name: ClassVar[str] = "g4_cpi_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Consumer Price Inflation - Monthly Collection (RBA G4), monthly, from Apr 2024. "
        "All-groups CPI index level (Sep 2025 = 100), monthly change and year-ended change in per cent, "
        "original and seasonally adjusted. Headline only, see g1_cpi_quarter for underlying measures."
    )
    table_no: ClassVar[str] = "g4"
