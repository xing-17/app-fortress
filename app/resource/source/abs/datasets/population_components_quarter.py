from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PopulationComponentsQuarterDataset(ABSDataset):
    """
    ABS Population Change and Components by State (dataflow ERP_COMP_Q), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "population_components_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ERP_COMP_Q"

    """

    name: ClassVar[str] = "population_components_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly population growth and its components by state and territory. "
        "Includes natural increase (births and deaths), "
        "net overseas migration, "
        "and net interstate migration. "
        "Geographic coverage: Australia/State."
    )
    dataflow_id: ClassVar[str] = "ERP_COMP_Q"
