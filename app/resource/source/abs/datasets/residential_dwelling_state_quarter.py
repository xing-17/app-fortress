from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class ResidentialDwellingStateQuarterDataset(ABSDataset):
    """
    ABS Residential Dwelling by state (dataflow RES_DWELL_ST), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "residential_dwelling_state_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "RES_DWELL_ST"

    """

    name: ClassVar[str] = "residential_dwelling_state_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Estimates of the total value, number and mean price of Australia's dwellings. "
        "Quarterly estimates of the total value, number and mean price of residential dwellings by state and territory. "
        "Unit of measure: AUD/Number. "
        "Geographic coverage: Australia/State. "
        "Catalogue number: 6416.0"
    )
    dataflow_id: ClassVar[str] = "RES_DWELL_ST"
