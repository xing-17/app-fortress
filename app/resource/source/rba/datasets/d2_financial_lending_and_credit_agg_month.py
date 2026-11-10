from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class D2FinancialLendingAndCreditAggMonthDataset(RBADataset):
    """
    RBA Lending and Credit Aggregates (table D2) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "d2_financial_lending_and_credit_agg_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "d2"

    """

    name: ClassVar[str] = "d2_financial_lending_and_credit_agg_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Lending and Credit Aggregates (RBA D2), monthly, from 1976, $ billion, outstanding levels. "
        "Credit (total, owner-occupier and investor housing, business, other personal), narrow credit, "
        "loans and advances by AFIs, banks and NBFIs, lending to government, bills on issue. "
        "Original and seasonally adjusted, with and without securitisations. "
        "Release may be delayed during the RBA D2A decommissioning."
    )
    table_no: ClassVar[str] = "d2"
