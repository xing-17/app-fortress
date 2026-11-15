from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: 1 Number of Established House Transfers, 2 Number of Attached Dwelling Transfers, 3 Median Price of Established House Transfers, 4 Median Price of Attached Dwelling Transfers.",
        ),
        ColumnDesc(
            name="REGION",
            description=(
                "State or Greater Capital City Statistical Area (GCCSA). "
                "AUS Australia, 1-8 states and territories (1 NSW, 2 Vic, 3 Qld, 4 SA, 5 WA, 6 Tas, 7 NT, 8 ACT), "
                "capital cities 1GSYD, 2GMEL, 3GBRI, 4GADE, 5GPER, 6GHOB, 7GDAR and 8ACTE, "
                "rest of state 1RNSW, 2RVIC, 3RQLD, 4RSAU, 5RWAU, 6RTAS and 7RNTE, "
                "100 weighted average of eight capital cities, 150 weighted average of rest of state."
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
