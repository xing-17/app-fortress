from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class F2_1GovBondRateMonthDataset(RBADataset):
    """
    RBA Capital Market Yields - Government Bonds (table F2.1) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "f2_1_gov_bond_rate_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "f2.1"

    """

    name: ClassVar[str] = "f2_1_gov_bond_rate_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Capital Market Yields - Government Bonds (RBA F2.1), monthly, from May 2013, per cent per annum. "
        "Interpolated Australian government bond yields at 2, 3, 5 and 10 year maturity "
        "and the 10 year indexed bond yield."
    )
    table_no: ClassVar[str] = "f2.1"
