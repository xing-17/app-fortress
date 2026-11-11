from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexCPICapitalQuarterDataset(ABSDataset):
    """
    ABS Consumer Price Index by capital city (dataflow CPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_cpi_capital_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "CPI"

    """

    name: ClassVar[str] = "price_index_cpi_capital_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Consumer Price Index (CPI) by capital city, "
        "including quarterly and monthly series (the REGION dimension selects the city, e.g. 1 is Sydney). "
        "Includes index numbers and percentage changes by expenditure category, such as Rents. "
        "Geographic coverage: Australia/Capital city."
    )
    dataflow_id: ClassVar[str] = "CPI"
