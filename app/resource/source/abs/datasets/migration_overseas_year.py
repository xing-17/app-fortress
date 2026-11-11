from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class MigrationOverseasYearDataset(ABSDataset):
    """
    ABS Net Overseas Migration (dataflow NOM_FY), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "migration_overseas_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        dataflow_id (str):
            ABS dataflow id, fixed to "NOM_FY"

    """

    name: ClassVar[str] = "migration_overseas_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    description: ClassVar[str] = (
        "Annual net overseas migration (NOM) by financial year, "
        "broken down by age, sex and state/territory. "
        "Geographic coverage: Australia/State."
    )
    dataflow_id: ClassVar[str] = "NOM_FY"
