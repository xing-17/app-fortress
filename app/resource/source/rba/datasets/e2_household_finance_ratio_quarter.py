from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class E2HouseholdFinanceRatioQuarterDataset(RBADataset):
    """
    RBA Household Finances - Selected Ratios (table E2) - Quarterly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "e2_household_finance_ratio_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "e2"

    """

    name: ClassVar[str] = "e2_household_finance_ratio_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Household Finances - Selected Ratios (RBA E2), quarterly, from 1988, per cent, "
        "original and seasonally adjusted. Ratios to annualised household disposable income: "
        "household debt, housing debt, owner-occupier housing debt, financial assets, housing assets, total assets; "
        "plus household debt to assets and housing debt to housing assets. "
        "Ratios only, no $ balance sheet levels and no interest payment ratio."
    )
    table_no: ClassVar[str] = "e2"
