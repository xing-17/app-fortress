from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class JobVacanciesQuarterDataset(ABSDataset):
    """
    ABS Job Vacancies (dataflow JV), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "job_vacancies_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "JV"

    """

    name: ClassVar[str] = "job_vacancies_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Estimates of job vacancies classified by industry, "
        "sector and state/territory. "
        "Job vacancies data relate to the number of vacancies which exist on the actual survey reference date only, "
        "and not for a monthly or quarterly period. "
    )
    dataflow_id: ClassVar[str] = "JV"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: M1 job vacancies, M2 standard error of job vacancies.",
        ),
        ColumnDesc(
            name="SECTOR",
            description="Sector of the employer: 7 Private and Public, 1 Private, 2 Public, 3 Commonwealth, 6 State and Local Government, 4 State Government, 5 Local Government.",
        ),
        ColumnDesc(
            name="INDUSTRY",
            description="ANZSIC 2006 industry: TOT All Industries or a division letter, e.g. A Agriculture, Forestry and Fishing, B Mining, C Manufacturing, E Construction, Q Health Care and Social Assistance.",
        ),
        ColumnDesc(
            name="TSEST",
            description="Adjustment type of the series: 10 Original, 20 Seasonally Adjusted, 30 Trend, 40 Sensitivity Upper, 50 Sensitivity Lower.",
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
        ColumnDesc(
            name="DECIMALS",
            description="Number of decimal places ABS publishes for the value.",
        ),
    ]
