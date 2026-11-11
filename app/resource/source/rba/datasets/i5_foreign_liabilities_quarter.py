from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class I5ForeignLiabilitiesQuarterDataset(RBADataset):
    """
    RBA Foreign Liabilities (table I5) - Quarterly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "i5_foreign_liabilities_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "i5"

    """

    name: ClassVar[str] = "i5_foreign_liabilities_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Australia's Net Foreign Liabilities (RBA I5), quarterly, from 1959, original. "
        "Net foreign debt, equity and total liabilities ($ million, from 1988), with debt liabilities split by "
        "official, non-official, private financial and private non-financial sector; "
        "net income deficit, net debt and equity income payments ($ million), "
        "and net income deficit and net debt income payments as per cent of GDP (seasonally adjusted). "
        "Net positions only, gross assets and liabilities are RBA I4."
    )
    table_no: ClassVar[str] = "i5"
