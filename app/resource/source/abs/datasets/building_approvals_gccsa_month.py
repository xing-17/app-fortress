from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class BuildingApprovalsGCCSAMonthDataset(ABSDataset):
    """
    ABS Building Approvals by GCCSA (dataflow BA_GCCSA), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "building_approvals_gccsa_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        dataflow_id (str):
            ABS dataflow id, fixed to "BA_GCCSA"

    """

    name: ClassVar[str] = "building_approvals_gccsa_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Dataset: BA_GCCSA. The monthly Building Approvals (BAPS) collects data relating to residential and non-residential building work. "
        "It provides estimates of future building activity and the sampling framework for the quarterly Building Activity Survey."
        "Which is a major contributor to the quarterly National Accounts estimates."
        "Unit of measure: AUD Number. "
        "Geographic coverage: Australia/State/GCCSA. "
        "Catalogue number: 8731.0"
    )
    dataflow_id: ClassVar[str] = "BA_GCCSA"
