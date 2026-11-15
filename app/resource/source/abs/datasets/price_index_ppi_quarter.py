from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class PriceIndexPPIQuarterDataset(ABSDataset):
    """
    ABS Producer Price Index (dataflow PPI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "price_index_ppi_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "PPI"

    """

    name: ClassVar[str] = "price_index_ppi_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly Producer Price Index (PPI), a measure of changes in the price of goods and services "
        "produced by businesses. "
        "Includes original, seasonally adjusted and trend series, with quarterly and annual changes, "
        "broken down by industry and by state/territory."
    )
    dataflow_id: ClassVar[str] = "PPI"
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
            description="Producer price index series code, naming an industry, product or stage of production, e.g. T11 Coal Mining Inputs, T18 House Construction Inputs.",
        ),
        ColumnDesc(
            name="TYPE",
            description="Direction of the index: INPUT prices paid by producers, OUTPUT prices received by producers.",
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
        ColumnDesc(
            name="BASE_PERIOD",
            description="Code of the base period of an index series, where the index equals 100, e.g. 25 is Sep 2025 = 100 in CPI and 2024-25 = 100 in LCI, PPI and WPI. Null for non-index measures.",
        ),
        ColumnDesc(
            name="DECIMALS",
            description="Number of decimal places ABS publishes for the value.",
        ),
    ]
