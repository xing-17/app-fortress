from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class PopulationComponentsGCCSAYearDataset(ABSDataset):
    """
    ABS Population Change and Components by ASGS 2021 regions (dataflow ERP_COMP_SA_ASGS2021), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "population_components_gccsa_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        dataflow_id (str):
            ABS dataflow id, fixed to "ERP_COMP_SA_ASGS2021"

    """

    name: ClassVar[str] = "population_components_gccsa_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    description: ClassVar[str] = (
        "Annual population change and its components "
        "(natural increase, net internal migration and net overseas migration) "
        "for ASGS 2021 regions, "
        "including Greater Capital City Statistical Areas (e.g. Greater Sydney) and SA2 and above. "
        "Geographic coverage: Australia/State/GCCSA/SA."
    )
    dataflow_id: ClassVar[str] = "ERP_COMP_SA_ASGS2021"
