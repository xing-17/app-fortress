from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class NationalAccountsAggQuarterDataset(ABSDataset):
    """
    ABS National Accounts Aggregates (dataflow ANA_AGG), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "national_accounts_agg_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "ANA_AGG"

    """

    name: ClassVar[str] = "national_accounts_agg_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Headline statistics from the quarterly national accounts. "
        "Includes gross domestic product (GDP), "
        "GDP per capita, "
        "real income measures, "
        "and the household saving ratio"
    )
    dataflow_id: ClassVar[str] = "ANA_AGG"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "Type of the figure: M1 chain volume measures, M2 chain volume measures percentage changes, M3 current prices, "
                "M4 current prices percentage changes, M5 index, M6 index percentage changes, M7 ratio."
            ),
        ),
        ColumnDesc(
            name="DATA_ITEM",
            description=(
                "Key aggregate: GPM Gross domestic product, GPM_PCA GDP per capita, GVA_MKT Gross value added market sector, NDP Net domestic product, "
                "RDI Real gross domestic income, NNDI Real net national disposable income, GNI Gross national income, SAV Net saving, "
                "HSR Household saving ratio, DFD Domestic final demand, TTR Terms of trade, GPM_HRW Hours worked, GPM_PHW GDP per hour worked, "
                "RULC_LAB Real unit of labour costs."
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
