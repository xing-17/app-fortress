from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class ResidentialDwellingGCCSAQuarterDataset(ABSDataset):
    """
    ABS Residential Dwelling by GCCSA (dataflow RES_DWELL), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "residential_dwelling_gccsa_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "RES_DWELL"

    """

    name: ClassVar[str] = "residential_dwelling_gccsa_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Estimates of the total value, number and mean price of Australia's dwellings. "
        "Quarterly unstratified median prices and transfer counts of residential dwellings by dwelling type, for Greater Capital City Statistical Areas and Rest of State. "
        "Unit of measure: AUD/Number. "
        "Geographic coverage: Australia/State/GCCSA. "
        "Catalogue number: 6432.0"
    )
    dataflow_id: ClassVar[str] = "RES_DWELL"
