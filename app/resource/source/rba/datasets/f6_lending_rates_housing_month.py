from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F6LendingRatesHousingMonthDataset(RBADataset):
    """
    RBA Housing Lending Rates (table F6) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f6_lending_rates_housing_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f6"

    """

    name: ClassVar[str] = "f6_lending_rates_housing_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Housing Lending Rates (RBA F6), monthly, from Jul 2019, per cent per annum. "
        "Average rates on new loans funded in the month and on outstanding loans, "
        "by owner-occupier or investor, fixed or variable rate, repayment type (interest-only, principal-and-interest), "
        "loan-to-valuation ratio, loan size and institution size."
    )
    table_no: ClassVar[str] = "f6"
