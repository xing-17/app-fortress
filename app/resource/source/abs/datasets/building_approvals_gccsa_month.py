from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
        "Before comparing with ABS headline figures (seasonally adjusted), check TSEST and read OBS_VALUE by UNIT_MEASURE and UNIT_MULT. "
        "Geographic coverage: Australia/State/GCCSA. "
        "Catalogue number: 8731.0"
    )
    dataflow_id: ClassVar[str] = "BA_GCCSA"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="What is measured: 1 number of dwelling units, 2 value of building jobs, 3 number of building jobs valued $50,000 or more.",
        ),
        ColumnDesc(
            name="VALUE",
            description=(
                "Dimension, not the observation: value band of the building job (the figure is in OBS_VALUE): 1 Total, 2 $50 million and over, 3 $20 million to less than $50 million, "
                "4 $5 million to less than $20 million, 5 $1 million to less than $5 million, "
                "6 $250,000 to less than $1 million, 7 $50,000 to less than $250,000."
            ),
        ),
        ColumnDesc(
            name="SECTOR",
            description="Ownership of the building: 9 Total Sectors, 1 Private Sector, 5 Public Sector.",
        ),
        ColumnDesc(
            name="WORK_TYPE",
            description=(
                "Type of building work: TOT Total Work, 1 New, 2 Alterations and additions, "
                "3 Alterations and additions creating dwellings, 4 Alterations and additions not creating dwellings, "
                "5 Relocation of dwellings, 6 Demolition of dwellings, 7 Conversions, "
                "8 Alterations and additions including conversions."
            ),
        ),
        ColumnDesc(
            name="BUILDING_TYPE",
            description=(
                "Type of building: TOT All Buildings, 100 Total Residential, 110 Houses, "
                "120 Semi-detached, row or terrace houses and townhouses, 130 Apartments, 150 Total Other Residential, "
                "200 Commercial, 300 Industrial and 400 Other Non-residential buildings. "
                "Codes below a total split it, e.g. 131 apartments in a one or two storey block, 210 retail and wholesale trade buildings."
            ),
        ),
        ColumnDesc(
            name="TSEST",
            description="Adjustment type of the series: 10 Original, 20 Seasonally Adjusted, 30 Trend, 40 Sensitivity Upper, 50 Sensitivity Lower.",
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
