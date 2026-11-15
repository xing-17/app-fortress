from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class LivingCostSelectedIndexesQuarterDataset(ABSDataset):
    """
    ABS Living Cost Selected Indexes (dataflow LCI), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "living_cost_selected_indexes_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "LCI"

    """

    name: ClassVar[str] = "living_cost_selected_indexes_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Dataset: LCI. Measures the price change of goods and services and its effect on living expenses of selected household types. "
        "Quarterly Selected Living Cost Indexes."
        "Measuring the effect of price changes on the out-of-pocket living expenses of selected household types (employee, age pensioner, other government transfer recipient, self-funded retiree). "
        "Unit of measure: Index/Percent. "
        "Geographic coverage: current snapshot holds REGION='50' (weighted average of eight capital cities) only. "
        "Catalogue number: 6467.0"
    )
    dataflow_id: ClassVar[str] = "LCI"
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
            description="Expenditure group of the index, e.g. 10001 All groups, 20001 Food and non-alcoholic beverages, 30002 Bread and cereal products, 40005 Bread.",
        ),
        ColumnDesc(
            name="HOUSHOLD_TYPE",
            description=(
                "Household type (the column name is spelled so by ABS): PBLCI Pensioner and beneficiary households, P1 Employee households, "
                "P2 Age pensioner households, P3 Other government transfer recipient households, P4 Self-funded retiree households."
            ),
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
            name="BASE_PERIOD",
            description="Code of the base period of an index series, where the index equals 100, e.g. 25 is Sep 2025 = 100 in CPI and 2024-25 = 100 in LCI, PPI and WPI. Null for non-index measures.",
        ),
    ]
