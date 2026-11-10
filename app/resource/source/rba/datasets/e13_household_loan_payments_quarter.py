from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class E13HouseholdLoanPaymentsQuarterDataset(RBADataset):
    """
    RBA Housing Loan Payments (table E13) - Quarterly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "e13_household_loan_payments_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "e13"

    """

    name: ClassVar[str] = "e13_household_loan_payments_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Housing Loan Payments (RBA E13), quarterly, from 2009, seasonally adjusted. "
        "Interest charged and scheduled repayments on housing loans (total, owner-occupied, investment, $ million), "
        "excess payments on total housing loans ($ million), "
        "and total interest, scheduled repayments and excess payments relative to household disposable income (per cent). "
        "Also the share of housing loan accounts with an offset or redraw account (per cent, original)."
    )
    table_no: ClassVar[str] = "e13"
