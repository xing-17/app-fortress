from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
            Update frequency, fixed to FrequencyOption.YEAR
        dataflow_id (str):
            ABS dataflow id, fixed to "ERP_ASGS2021"

    """

    name: ClassVar[str] = "population_estimates_sa2_year"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    description: ClassVar[str] = (
        "Annual estimated resident population (ERP) at 30 June by SA2 and above, "
        "ASGS Edition 3 boundaries, 2001 onwards. Used at Greater Sydney (GCCSA) "
        "level for a boundary-consistent population series."
    )
    dataflow_id: ClassVar[str] = "ERP_ASGS2021"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: ERP Estimated Resident Population.",
        ),
        ColumnDesc(
            name="SEX",
            description="Sex: 1 Males, 2 Females, 3 Persons.",
        ),
        ColumnDesc(
            name="AGE",
            description="Age: TOT All ages, single years such as 51, or five-year groups coded A<first age> such as A04 for 0-4 and A59 for 5-9.",
        ),
        ColumnDesc(
            name="REGION_TYPE",
            description="Type of the geography in REGION, e.g. AUS Australia, STE States and Territories, GCCSA Greater Capital City Statistical Areas, SA4, SA3 and SA2 Statistical Area Levels 4, 3 and 2.",
        ),
        ColumnDesc(
            name="ASGS_2021",
            description="Region code in ASGS Edition 3 (2021), its length follows REGION_TYPE: AUS Australia, 1 New South Wales, 1GSYD Greater Sydney, 3-digit SA4 (102), 5-digit SA3 (10201), 9-digit SA2 (102011028).",
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
    ]
