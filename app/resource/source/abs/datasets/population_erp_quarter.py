from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PopulationERPQuarterDataset(ABSDataset):
    """
    ABS Estimated Resident Population by State (dataflow ERP_Q), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "population_erp_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ERP_Q"

    """

    name: ClassVar[str] = "population_erp_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimated resident population (ERP) by state and territory, "
        "broken down by sex and age. "
        "Geographic coverage: Australia/State."
    )
    dataflow_id: ClassVar[str] = "ERP_Q"
