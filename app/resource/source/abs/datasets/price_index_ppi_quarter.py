from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexPPIQuarterDataset(ABSDataset):
    """
    ABS Producer Price Index (dataflow PPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_ppi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "PPI"

    """

    name: ClassVar[str] = "price_index_ppi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Producer Price Index (PPI), a measure of changes in the price of goods and services "
        "produced by businesses. "
        "Includes original, seasonally adjusted and trend series, with quarterly and annual changes, "
        "broken down by industry and by state/territory."
    )
    dataflow_id: ClassVar[str] = "PPI"
