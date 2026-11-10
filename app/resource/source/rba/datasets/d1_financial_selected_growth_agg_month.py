from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class D1FinancialSelectedGrowthAggMonthDataset(RBADataset):
    """
    RBA Growth in Selected Financial Aggregates (table D1) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "d1_financial_selected_growth_agg_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "d1"

    """

    name: ClassVar[str] = "d1_financial_selected_growth_agg_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Growth in Selected Financial Aggregates (RBA D1), monthly, from 1976, per cent, seasonally adjusted. "
        "Monthly and 12-month-ended growth of broad money, M3 and credit "
        "(total, owner-occupier and investor housing, business, other personal), including securitisations. "
        "Growth rates only, see d2_financial_lending_and_credit_agg_month for $ levels. "
        "Release may be delayed during the RBA D2A decommissioning."
    )
    table_no: ClassVar[str] = "d1"
