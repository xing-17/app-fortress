from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsIndGvaQuarterDataset(ABSDataset):
    """
    ABS National Accounts Industry GVA (dataflow ANA_IND_GVA), partitioned by snapshotdate

    Description:
    ----------
        Quarterly estimates of the Production approach of measuring Gross Domestic Product (GDP (P)),
        measured in chain volume measures.
        Includes estimates of gross value added by industry and subdivision,
        and taxes less subsidies on products.

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_ind_gva_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_IND_GVA"

    """

    name: ClassVar[str] = "national_accounts_ind_gva_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of the Production approach of measuring Gross Domestic Product (GDP (P)), "
        "measured in chain volume measures. "
        "Includes estimates of gross value added by industry and subdivision, "
        "and taxes less subsidies on products."
    )
    dataflow_id: ClassVar[str] = "ANA_IND_GVA"
