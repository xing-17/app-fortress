from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexWPIQuarterDataset(ABSDataset):
    """
    ABS Wage Price Index (dataflow WPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_wpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "WPI"

    """

    name: ClassVar[str] = "price_index_wpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Wage Price Index (WPI), a measure of changes in the price of labour "
        "that is unaffected by shifts in the composition of the labour force, hours worked "
        "or employee characteristics. "
        "Includes total hourly rates of pay excluding bonuses (original, seasonally adjusted "
        "and trend series, with quarterly and annual changes), broken down by sector, industry "
        "and state/territory, and by method of setting pay."
    )
    dataflow_id: ClassVar[str] = "WPI"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Type of the figure: 1 Quarterly Index, 2 Percentage change from previous quarter, "
                "3 Percentage change from corresponding quarter of previous year, 4 Financial Year Index, "
                "5 Financial Year Index percentage change from previous period."
            ),
        ),
        ColumnDesc(
            name="INDEX",
            description="Pay concept: OHRPEB Ordinary time hourly rates of pay excluding bonuses, OHRPIB Ordinary time hourly rates of pay including bonuses, THRPEB Total hourly rates of pay excluding bonuses, THRPIB Total hourly rates of pay including bonuses.",
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
            name="BASE_PERIOD",
            description="Code of the base period of an index series, where the index equals 100, e.g. 25 is Sep 2025 = 100 in CPI and 2024-25 = 100 in LCI, PPI and WPI. Null for non-index measures.",
        ),
    ]
