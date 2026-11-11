from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class MigrationInterstateQuarterDataset(ABSDataset):
    """
    ABS Interstate Migration (dataflow ABS_DEM_QIM), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "migration_interstate_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ABS_DEM_QIM"

    """

    name: ClassVar[str] = "migration_interstate_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly interstate migration flows between states and territories. "
        "Includes arrivals and departures by state of origin and destination. "
        "Geographic coverage: Australia/State."
    )
    dataflow_id: ClassVar[str] = "ABS_DEM_QIM"
