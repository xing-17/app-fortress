from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: 1 Value of dwelling stock owned by all sectors, 2 Value of dwelling stock owned by households, 3 Value of dwelling stock owned by non households, 4 Number of residential dwellings, 5 Mean price of residential dwellings.",
        ),
        ColumnDesc(
            name="REGION",
            description=(
                "State or territory: AUS Australia, 1 New South Wales, 2 Victoria, 3 Queensland, 4 South Australia, "
                "5 Western Australia, 6 Tasmania, 7 Northern Territory, 8 Australian Capital Territory, 9 Other Territories."
            ),
        ),
        ColumnDesc(
            name="FREQ",
            description="Frequency of the series: A annual, Q quarterly, M monthly.",
        ),
        ColumnDesc(
            name="UNIT_MULT",
            description="Power-of-ten multiplier of OBS_VALUE, the figure in UNIT_MEASURE is OBS_VALUE x 10^UNIT_MULT, e.g. 0 units, 3 thousands, 6 millions.",
        ),
    ]
