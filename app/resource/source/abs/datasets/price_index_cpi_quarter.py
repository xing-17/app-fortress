from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexCPIQuarterDataset(ABSDataset):
    """
    ABS Consumer Price Index (dataflow CPI_Q), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_cpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "CPI_Q"

    """

    name: ClassVar[str] = "price_index_cpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Consumer Price Index (CPI), a measure of changes in the price of a basket of goods and services "
        "purchased by households. "
        "Includes original, seasonally adjusted and trend series, with quarterly and annual changes, "
        "broken down by expenditure category, and by state/territory."
    )
    dataflow_id: ClassVar[str] = "CPI_Q"
