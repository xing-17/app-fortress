from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.abs.dataset import ABSDataset


class BuildingActivityStateQuarterDataset(ABSDataset):
    """
    ABS Building Activity by State (dataflow BUILDING_ACTIVITY), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "building_activity_state_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "BUILDING_ACTIVITY"

    """

    name: ClassVar[str] = "building_activity_state_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Dataset: BUILDING_ACTIVITY. Building Activity. "
        "Provides estimates of value of building work and number of dwellings commenced, completed, under construction and in the pipeline. "
        "Unit of measure: AUD Units. "
        "Geographic coverage: Australia/State. "
        "Catalogue number: 8752.0"
    )
    dataflow_id: ClassVar[str] = "BUILDING_ACTIVITY"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *ABSDataset.column_descs,
        ColumnDesc(
            name="MEASURE",
            description=(
                "What is measured: M1 value of work done during the quarter, M2 value of work yet to be done, "
                "M3 value of work commenced, M4 value of work completed, M5 value of work under construction, "
                "M6 dwelling units commenced, M7 dwelling units completed, M8 dwelling units under construction."
            ),
        ),
        ColumnDesc(
            name="REGION",
            description=(
                "State or territory: AUS Australia, 1 New South Wales, 2 Victoria, 3 Queensland, 4 South Australia, "
                "5 Western Australia, 6 Tasmania, 7 Northern Territory, 8 Australian Capital Territory, 9 Other Territories."
            ),
        ),
        ColumnDesc(
            name="PRICE_ADJ",
            description="Price basis of the value: CUR Current Price, CVM Chain Volume Measures, IPD Implicit Price Deflator.",
        ),
        ColumnDesc(
            name="BLD_WORK_TYPE",
            description=(
                "Type of building work: TOT Total Work, 1 New, 2 Alterations and additions, "
                "3 Alterations and additions creating dwellings, 4 Alterations and additions not creating dwellings, "
                "5 Relocation of dwellings, 6 Demolition of dwellings, 7 Conversions, "
                "8 Alterations and additions including conversions."
            ),
        ),
        ColumnDesc(
            name="SECTOR_OWN",
            description="Ownership of the building: 9 Total Sectors, 1 Private Sector, 5 Public Sector.",
        ),
        ColumnDesc(
            name="TYPE_BLDG",
            description=(
                "Type of building: TOT All Buildings, 100 Total Residential, 110 Houses, "
                "120 Semi-detached, row or terrace houses and townhouses, 130 Flats, units or apartments, 150 Total Other Residential, "
                "700 Total Non-residential, 200 Commercial, 300 Industrial, 400 Other Non-residential buildings, "
                "plus 800 Dwellings excluding new residential and 850 Dwellings excluding houses. "
                "Three-digit codes below a total split it by storeys or purpose, e.g. 121 one storey, 210 retail and wholesale trade buildings."
            ),
        ),
        ColumnDesc(
            name="TSEST",
            description="Adjustment type of the series: 10 Original, 20 Seasonally Adjusted, 30 Trend, 40 Sensitivity Upper, 50 Sensitivity Lower.",
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
