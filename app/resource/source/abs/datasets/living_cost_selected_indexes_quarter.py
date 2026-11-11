from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
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
        "Geographic coverage: Australia/State. "
        "Catalogue number: 6467.0"
    )
    dataflow_id: ClassVar[str] = "LCI"
