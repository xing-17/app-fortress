from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class MigrationRegionalRecentYearDataset(ABSDataset):
    """
    ABS Regional Migration, 2016-17 to 2019-20 on ASGS 2016 (dataflow ABS_REGIONAL_MIGRATION), partitioned by snapshotdate

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
        "Net internal and overseas migration estimates by region (SA2 and above) and age, 2016-17 to 2019-20, "
        "on ASGS 2016 boundaries. Later years are in population_components_gccsa_year (ASGS 2021, from 2021-22), "
        "so joining the two leaves a gap and needs boundary and measure checks."
    )
    dataflow_id: ClassVar[str] = "ABS_REGIONAL_MIGRATION"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MIG_TYPE",
            description="Kind of migration: 6 Net Internal Migration, 9 Net Overseas Migration.",
        ),
        ColumnDesc(
            name="REGIONTYPE",
            description="Type of the geography in ASGS_2016, e.g. AUS Australia, STE States and Territories, GCCSA Greater Capital City Statistical Areas, SA4, SA3 and SA2 Statistical Area Levels 4, 3 and 2.",
        ),
        ColumnDesc(
            name="ASGS_2016",
            description="Region code in ASGS 2016, its length follows REGIONTYPE: 0 Australia, 1-digit state or territory (1 New South Wales), 3-digit SA4 (101), 5-digit SA3 (10102), 9-digit SA2 (101021007).",
        ),
        ColumnDesc(
            name="AGE",
            description="Age: single years such as 6, five-year groups coded A<first age> such as A04 for 0-4 and A10 for 10-14, and 6599 for 65 and over.",
        ),
        ColumnDesc(
            name="FREQUENCY",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
    ]
