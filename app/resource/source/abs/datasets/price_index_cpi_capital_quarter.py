from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexCPICapitalQuarterDataset(ABSDataset):
    """
    ABS Consumer Price Index by capital city (dataflow CPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_cpi_capital_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "CPI"

    """

    name: ClassVar[str] = "price_index_cpi_capital_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Consumer Price Index (CPI) by capital city, "
        "including quarterly and monthly series (the REGION dimension selects the city, e.g. 1 is Sydney). "
        "Includes index numbers and percentage changes by expenditure category, such as Rents. "
        "Geographic coverage: Australia/Capital city. "
        "Monthly and quarterly records are mixed, always filter FREQ (M or Q)."
    )
    dataflow_id: ClassVar[str] = "CPI"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Type of the figure: 1 index numbers, 2 percentage change from previous period, 3 percentage change from previous year, "
                "4 contribution to CPI index number, 5 change in contribution to CPI index number, "
                "6 contribution to percentage points change from previous period, 7 contribution to annual percentage points change."
            ),
        ),
        ColumnDesc(
            name="INDEX",
            description="CPI expenditure group, e.g. 10001 All groups CPI, 20001 Food and non-alcoholic beverages, 30002 Bread and cereal products, 40005 Bread.",
        ),
        ColumnDesc(
            name="TSEST",
            description="Adjustment type of the series: 10 Original, 20 Seasonally Adjusted, 30 Trend, 40 Sensitivity Upper, 50 Sensitivity Lower.",
        ),
        ColumnDesc(
            name="REGION",
            description="Capital city: 50 Australia, 1 Sydney, 2 Melbourne, 3 Brisbane, 4 Adelaide, 5 Perth, 6 Hobart, 7 Darwin, 8 Canberra.",
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
        ColumnDesc(
            name="DECIMALS",
            description="Number of decimal places ABS publishes for the value.",
        ),
        ColumnDesc(
            name="BASE_PERIOD",
            description="Code of the base period of an index series, where the index equals 100, e.g. 25 is Sep 2025 = 100 in CPI and 2024-25 = 100 in LCI, PPI and WPI. Null for non-index measures.",
        ),
    ]
