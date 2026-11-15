from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsExpQuarterDataset(ABSDataset):
    """
    ABS National Accounts Expenditure (dataflow ANA_EXP), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_exp_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_EXP"

    """

    name: ClassVar[str] = "national_accounts_exp_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Quarterly estimates of the Expenditure approach of Gross Domestic Product (GDP (E)), "
        "measured in chain volume measures and current prices. "
        "Includes household and government expenditure, "
        "private and public sector investment, "
        "changes in inventories, "
        "and exports and imports of goods and services. "
    )
    dataflow_id: ClassVar[str] = "ANA_EXP"
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
                "Expenditure component of GDP, e.g. FCE Final consumption expenditure, GFC Gross fixed capital formation "
                "(GFC_DWL dwellings, GFC_EQP machinery and equipment, GFC_IPP intellectual property products and other GFC_ parts), "
                "DFD Domestic final demand, IST Changes in inventories, GNE Gross national expenditure."
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
