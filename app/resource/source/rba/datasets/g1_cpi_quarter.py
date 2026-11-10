from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class G1CPIQuarterDataset(RBADataset):
    """
    RBA Consumer Price Inflation - Quarterly (table G1), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "g1_cpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "g1"

    """

    name: ClassVar[str] = "g1_cpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Consumer Price Inflation (RBA G1), quarterly, from 1922. "
        "All-groups CPI index level, quarterly and year-ended change in per cent, plus underlying measures "
        "(trimmed mean, weighted median, tradables, non-tradables, excluding volatile items and interest charges). "
        "Original and seasonally adjusted."
    )
    table_no: ClassVar[str] = "g1"
