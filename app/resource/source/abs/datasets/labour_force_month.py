from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class LabourForceMonthDataset(ABSDataset):
    """
    ABS Labour Force (dataflow LF), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "labour_force_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        dataflow_id (str):
            ABS dataflow id, fixed to "LF"

    """

    name: ClassVar[str] = "labour_force_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Headline estimates of employment, "
        "unemployment, "
        "underemployment, "
        "participation and hours worked from the monthly Labour Force Survey."
    )
    dataflow_id: ClassVar[str] = "LF"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "What is measured: M1 employed full-time, M2 employed part-time, M3 employed persons, "
                "M4 unemployed looking for full-time work, M5 unemployed looking for part-time work, M6 unemployed persons, "
                "M7 labour force full-time, M8 labour force part-time, M9 labour force, M10 not in the labour force, M11 civilian population, "
                "M12 participation rate, M13 unemployment rate, M14 and M15 unemployment rate looking for full-time and part-time work, "
                "M16 employment to population ratio, M17 unemployment to population ratio looking for full-time work, "
                "M18 to M20 monthly hours worked in all jobs (employed persons, full-time, part-time), "
                "M21 to M23 underemployment (total, ratio of employed, rate of labour force), M24 underutilisation rate, "
                "M25 to M30 underemployed by full-time or part-time status, in standard and expanded analytical series."
            ),
        ),
        ColumnDesc(
            name="SEX",
            description="Sex: 1 Males, 2 Females, 3 Persons.",
        ),
        ColumnDesc(
            name="AGE",
            description="Age group: 1599 Total (age), 1564 15-64 years, 1524 15-24 years, 2534 25-34 years, 3544 35-44 years, 4554 45-54 years, 5564 55-64 years, 5599 55 years and over, 6599 65 years and over, also single years and narrower bands such as 1519 and 2024.",
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
