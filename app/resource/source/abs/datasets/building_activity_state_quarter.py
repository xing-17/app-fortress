from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class BuildingActivityStateQuarterDataset(ABSDataset):
    """
    ABS Building Activity by State (dataflow BUILDING_ACTIVITY), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "building_activity_state_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "BUILDING_ACTIVITY"

    """

    name: ClassVar[str] = "building_activity_state_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Dataset: BUILDING_ACTIVITY. Building Activity. "
        "Provides estimates of value of building work and number of dwellings commenced, completed, under construction and in the pipeline. "
        "Unit of measure: AUD Units. "
        "Geographic coverage: Australia/State. "
        "Catalogue number: 8752.0"
    )
    dataflow_id: ClassVar[str] = "BUILDING_ACTIVITY"
