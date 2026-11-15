from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: 1 Estimated Resident Population, 2 ERP Change Over Previous Year, 3 ERP Percentage Change Over Previous Year.",
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
    ]
