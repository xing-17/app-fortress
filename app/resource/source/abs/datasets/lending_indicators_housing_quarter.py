from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
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
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description="Kind of figure: FIN_NUM number, FIN_VAL value, FIN_AVG average, FIN_PCT percent, FIN_RATIO ratio.",
        ),
        ColumnDesc(
            name="DATA_ITEM",
            description=(
                "Lending indicator, e.g. NEWCOMMITS new loan commitments, NEWAPPLS new applications received, "
                "CREDITOUTSTCURRMTH credit outstanding at the end of the month, TOTFACILITIES total lending facilities, "
                "TOTCRED total credit available, DDOWNS_NEW drawdowns for new loans, SCHEDREPAY scheduled repayments, "
                "NETWRITEOFF net write-offs, REDRAWAVAIL available redraw balances, OFFSETBALCLOS closing balance of offset accounts. "
                "A suffix narrows the item, e.g. _SECRP secured by residential property, _FSI serviced by foreign-sourced income."
            ),
        ),
        ColumnDesc(
            name="LOAN_TYPE",
            description=(
                "Type of loan: DV8575 Total fixed term loans, revolving credit and other finance, DV8368 Total fixed term loans and revolving credit, "
                "DV8270 Fixed term loans, DV8269 Revolving credit, DV8338 Credit cards, DV8340 Margin loans, "
                "DV8337 Other revolving credit, DV8375 Other finance, DV8540 Bill acceptances, DV8541 Finance leases."
            ),
        ),
        ColumnDesc(
            name="LOAN_PURPOSE",
            description=(
                "Purpose of the loan, e.g. TOTLOANPURP Total purpose including refinancing, TOTLOANPURP_EXCLREFIN Total purpose excluding refinancing, "
                "TOTHOUS Total housing excluding refinancing, TOTDWELL Total dwellings excluding refinancing, "
                "DV8545 Purchase of residential land, DV8353 Construction of dwellings, DV8348 External refinancing, DV8349 Internal refinancing."
            ),
        ),
        ColumnDesc(
            name="LENDER_TYPE",
            description="Type of lender: TOT Total lender type, MAJ_B Major Banks, OTH_ADI Other ADIs, NON_ADI Non-ADIs.",
        ),
        ColumnDesc(
            name="HOUSING_PURPOSE",
            description=(
                "Housing purpose of the borrower: TOT Total housing purpose, DV5167 Owner occupier, DV5168 Investor, "
                "TOT_FHB Total First Home Buyers, DV5167_FHB Owner occupier First Home Buyers, DV5168_FHB Investor First Home Buyers, "
                "DV5167_NONFHB Owner occupier Non-First Home Buyers, DV8394 Non-resident."
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
