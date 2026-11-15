from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexCPIQuarterDataset(ABSDataset):
    """
    ABS Consumer Price Index (dataflow CPI_Q), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_cpi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "CPI_Q"

    """

    name: ClassVar[str] = "price_index_cpi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Consumer Price Index (CPI), a measure of changes in the price of a basket of goods and services "
        "purchased by households. "
        "Includes original, seasonally adjusted and trend series, with quarterly and annual changes, "
        "broken down by expenditure category. "
        "Quarterly only. The current snapshot holds REGION='50' (weighted average of eight capital cities) only; "
        "use price_index_cpi_capital_quarter for individual capital cities."
    )
    dataflow_id: ClassVar[str] = "CPI_Q"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Type of the figure: 1 index number, 2 percentage change from the previous period, "
                "3 percentage change from the corresponding quarter of the previous year, "
                "4 points contribution to the total index, 5 change in contribution to the total index."
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
            description="Capital city: 50 weighted average of eight capital cities, 1 Sydney, 2 Melbourne, 3 Brisbane, 4 Adelaide, 5 Perth, 6 Hobart, 7 Darwin, 8 Canberra.",
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
        ColumnDesc(
            name="DECIMALS",
            description="Number of decimal places ABS publishes for the value.",
        ),
    ]
