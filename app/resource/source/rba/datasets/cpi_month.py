from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class CPIMonthDataset(RBADataset):
    """
    RBA Consumer Price Index - Monthly (table G4), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "cpi_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        table_no (str):
            RBA statistical table number, fixed to "g4"

    """

    name: ClassVar[str] = "cpi_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = "Dataset for RBA Consumer Price Index. Monthly CPI data."
    table_no: ClassVar[str] = "g4"
