from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class MigrationRegionalArchivedYearDataset(ABSDataset):
    """
    ABS Regional Internal Migration Estimates, 2006-07 to 2015-16 (dataflow RIME_REGION), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "migration_regional_archived_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        dataflow_id (str):
            ABS dataflow id, fixed to "RIME_REGION"

    """

    name: ClassVar[str] = "migration_regional_archived_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    description: ClassVar[str] = (
        "Regional internal migration estimates by region (SA2 and above), "
        "2006-07 to 2015-16. Combined with ABS_REGIONAL_MIGRATION for a Greater "
        "Sydney series from 2006-07."
    )
    dataflow_id: ClassVar[str] = "RIME_REGION"
