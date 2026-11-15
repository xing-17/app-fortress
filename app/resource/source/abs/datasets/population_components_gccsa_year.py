from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="POP_COMP",
            description=(
                "Population component: 1 Births, 2 Deaths, 3 Natural Increase, 4 Internal Arrivals, 5 Internal Departures, "
                "6 Net Internal Migration, 7 Overseas Arrivals, 8 Overseas Departures, 9 Net Overseas Migration, 10 Estimated Resident Population."
            ),
        ),
        ColumnDesc(
            name="REGION_TYPE",
            description="Type of the geography in REGION, e.g. AUS Australia, STE States and Territories, GCCSA Greater Capital City Statistical Areas, SA4, SA3 and SA2 Statistical Area Levels 4, 3 and 2.",
        ),
        ColumnDesc(
            name="REGION",
            description="Region code in ASGS Edition 3 (2021), its length follows REGION_TYPE: AUS Australia, 1 New South Wales, 1GSYD Greater Sydney, 3-digit SA4 (102), 5-digit SA3 (10201), 9-digit SA2 (102011028).",
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
    ]
