from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class MigrationRegionalRecentYearDataset(ABSDataset):
    """
    ABS Regional Migration, 2016-17 onwards (dataflow ABS_REGIONAL_MIGRATION), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "migration_regional_recent_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        dataflow_id (str):
            ABS dataflow id, fixed to "ABS_REGIONAL_MIGRATION"

    """

    name: ClassVar[str] = "migration_regional_recent_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    description: ClassVar[str] = (
        "Net internal and overseas migration estimates by region (SA2 and above) and age, 2016-17 onwards."
    )
    dataflow_id: ClassVar[str] = "ABS_REGIONAL_MIGRATION"
