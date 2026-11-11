from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexWPIQuarterDataset(ABSDataset):
    """
    ABS Wage Price Index (dataflow WPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_wpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "WPI"

    """

    name: ClassVar[str] = "price_index_wpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Wage Price Index (WPI), a measure of changes in the price of labour "
        "that is unaffected by shifts in the composition of the labour force, hours worked "
        "or employee characteristics. "
        "Includes total hourly rates of pay excluding bonuses (original, seasonally adjusted "
        "and trend series, with quarterly and annual changes), broken down by sector, industry "
        "and state/territory, and by method of setting pay."
    )
    dataflow_id: ClassVar[str] = "WPI"
