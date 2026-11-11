from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PopulationEstimatesSA2YearDataset(ABSDataset):
    """
    ABS Estimated Resident Population by State (dataflow ERP_Q), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "population_estimates_sa2_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ERP_ASGS2021"

    """

    name: ClassVar[str] = "population_estimates_sa2_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Annual estimated resident population (ERP) at 30 June by SA2 and above, "
        "ASGS Edition 3 boundaries, 2001 onwards. Used at Greater Sydney (GCCSA) "
        "level for a boundary-consistent population series."
    )
    dataflow_id: ClassVar[str] = "ERP_ASGS2021"
