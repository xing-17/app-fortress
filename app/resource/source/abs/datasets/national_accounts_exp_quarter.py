from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsExpQuarterDataset(ABSDataset):
    """
    ABS National Accounts Expenditure (dataflow ANA_EXP), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_exp_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_EXP"

    """

    name: ClassVar[str] = "national_accounts_exp_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of the Expenditure approach of Gross Domestic Product (GDP (E)), "
        "measured in chain volume measures and current prices. "
        "Includes household and government expenditure, "
        "private and public sector investment, "
        "changes in inventories, "
        "and exports and imports of goods and services. "
    )
    dataflow_id: ClassVar[str] = "ANA_EXP"
