from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class LendingIndicatorsHousingQuarterDataset(ABSDataset):
    """
    ABS Lending Indicators for housing (dataflow LEND_HOUSING), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "lending_indicators_housing_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "LEND_HOUSING"

    """

    name: ClassVar[str] = "lending_indicators_housing_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Housing finance commitments, "
        "split by owner-occupier and investor lending and by first home buyers. "
        "Geographic coverage: Australia/State."
    )
    dataflow_id: ClassVar[str] = "LEND_HOUSING"
