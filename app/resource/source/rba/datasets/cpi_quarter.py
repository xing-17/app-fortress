from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class CPIQuarterDataset(RBADataset):
    """
    RBA Consumer Price Inflation - Quarterly (table G1), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "cpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        table_no (str):
            RBA statistical table number, fixed to "g1"

    """

    name: ClassVar[str] = "cpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = "Dataset for RBA Consumer Price Inflation. Quarterly CPI data."
    table_no: ClassVar[str] = "g1"
