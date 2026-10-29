from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsSfdQuarterDataset(ABSDataset):
    """
    ABS National Accounts State Final Demand (dataflow ANA_SFD), partitioned by snapshotdate

    Description:
    ----------
        Quarterly estimates of state final demand (SFD) and component series,
        measured in chain volume measures.
        Includes household and government expenditure,
        private and public sector investment,
        and compensation of employees by state.

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_sfd_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_SFD"

    """

    name: ClassVar[str] = "national_accounts_sfd_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of state final demand (SFD) and component series, "
        "measured in chain volume measures. "
        "Includes household and government expenditure, "
        "private and public sector investment, "
        "and compensation of employees by state"
    )
    dataflow_id: ClassVar[str] = "ANA_SFD"
