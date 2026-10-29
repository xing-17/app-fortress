from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class LabourForceMonthDataset(ABSDataset):
    """
    ABS Labour Force (dataflow LF), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "labour_force_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        dataflow_id (str):
            ABS dataflow id, fixed to "LF"

    """

    name: ClassVar[str] = "labour_force_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Headline estimates of employment, "
        "unemployment, "
        "underemployment, "
        "participation and hours worked from the monthly Labour Force Survey."
    )
    dataflow_id: ClassVar[str] = "LF"
