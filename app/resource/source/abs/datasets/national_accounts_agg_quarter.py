from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsAggQuarterDataset(ABSDataset):
    """
    ABS National Accounts Aggregates (dataflow ANA_AGG), partitioned by snapshotdate

    Description:
    ----------
        Headline statistics from the quarterly national accounts.
        Includes gross domestic product (GDP),
        GDP per capita,
        real income measures,
        and the household saving ratio

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_agg_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_AGG"

    """

    name: ClassVar[str] = "national_accounts_agg_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Headline statistics from the quarterly national accounts. "
        "Includes gross domestic product (GDP), "
        "GDP per capita, "
        "real income measures, "
        "and the household saving ratio"
    )
    dataflow_id: ClassVar[str] = "ANA_AGG"
