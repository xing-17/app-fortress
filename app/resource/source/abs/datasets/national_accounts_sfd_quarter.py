from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsSfdQuarterDataset(ABSDataset):
    """
    ABS National Accounts State Final Demand (dataflow ANA_SFD), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_sfd_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_SFD"

    """

    name: ClassVar[str] = "national_accounts_sfd_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of state final demand (SFD) and component series, "
        "measured in chain volume measures. "
        "Includes household and government expenditure, "
        "private and public sector investment, "
        "and compensation of employees by state. "
        "Some series carry UNIT_MEASURE='NA', "
        "so check MEASURE and DATA_ITEM against the ABS table before reading OBS_VALUE as money."
    )
    dataflow_id: ClassVar[str] = "ANA_SFD"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Type of the figure: VCH chain volume measures, C current prices, FCH chain price indexes, DCH implicit price deflators, "
                "ICH index, TCH and TC contributions to growth (chain volume and current prices), R ratio. "
                "PCT_VCH, PCT_C, PCT_FCH, PCT_DCH and PCT_ICH are the percentage changes of the same figures, "
                "PCT_RCH, RC and PCT_RC are revisions."
            ),
        ),
        ColumnDesc(
            name="DATA_ITEM",
            description=(
                "State final demand component, e.g. FCE_ household final consumption expenditure by purpose "
                "(FCE_FNAH Food, FCE_HLTH Health, FCE_ALTH Alcoholic beverages), GFC Gross fixed capital formation and its parts."
            ),
        ),
        ColumnDesc(
            name="SECTOR",
            description=(
                "Institutional sector: SSS all sectors, PSS private, GSS public, PHS households, GGS general government, "
                "PTS private non-financial corporations, GTS public non-financial corporations, NFS non-financial corporations, "
                "SFS financial corporations, TCS total corporations, SOS non-residents, MSS market sector."
            ),
        ),
        ColumnDesc(
            name="TSEST",
            description="Adjustment type of the series: 10 Original, 20 Seasonally Adjusted, 30 Trend, 40 Sensitivity Upper, 50 Sensitivity Lower.",
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
