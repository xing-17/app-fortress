from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="RIM",
            description="Direction of internal migration: 1 Arrivals, 2 Departures, 3 Net.",
        ),
        ColumnDesc(
            name="REGION_TYPE",
            description="Type of the geography in REGION, e.g. AUS Australia, STE States and Territories, GCCSA Greater Capital City Statistical Areas, SA4, SA3 and SA2 Statistical Area Levels 4, 3 and 2.",
        ),
        ColumnDesc(
            name="ASGS_2011_STATE_GCCSA_SA4_SA3_SA2",
            description="Region code in ASGS 2011, its length follows REGION_TYPE: 0 Australia, 1-digit state or territory (4 South Australia), 3-digit SA4 (401), 5-digit SA3 (40104), 9-digit SA2 (401041014).",
        ),
        ColumnDesc(
            name="FREQUENCY",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
    ]
