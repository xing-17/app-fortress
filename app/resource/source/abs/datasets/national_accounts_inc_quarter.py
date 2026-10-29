from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsIncQuarterDataset(ABSDataset):
    """
    ABS National Accounts Income (dataflow ANA_INC), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_inc_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_INC"

    """

    name: ClassVar[str] = "national_accounts_inc_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of the Income approach of measuring Gross Domestic Product (GDP (I)), "
        "measured in current prices. "
        "Includes estimates of compensation of employees, "
        "gross operating surplus, "
        "gross mixed income, "
        "and taxes less subsidies on production and imports"
    )
    dataflow_id: ClassVar[str] = "ANA_INC"
