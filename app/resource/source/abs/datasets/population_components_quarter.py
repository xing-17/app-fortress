from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Population component: 1 Births, 2 Deaths, 3 Natural Increase, 4 Internal Arrivals, 5 Internal Departures, "
                "6 Net Internal Migration, 7 Overseas Arrivals, 8 Overseas Departures, 9 Net Overseas Migration, 10 Estimated Resident Population, "
                "11 Net Permanent and Long Term Movement, 12 Migration Adjustment, 13 Change Over Previous Quarter."
            ),
        ),
        ColumnDesc(
            name="REGION",
            description=(
                "State or territory: AUS Australia, 1 New South Wales, 2 Victoria, 3 Queensland, 4 South Australia, "
                "5 Western Australia, 6 Tasmania, 7 Northern Territory, 8 Australian Capital Territory, 9 Other Territories."
            ),
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
        ColumnDesc(
            name="UNIT_MULT",
            description="Power-of-ten multiplier of OBS_VALUE, the figure in UNIT_MEASURE is OBS_VALUE x 10^UNIT_MULT, e.g. 0 units, 3 thousands, 6 millions.",
        ),
    ]
