from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.nswvg.dataset import NSWVGDataset
from app.resource.source.nswvg.provision import NSWVGProvisionKind


class YearPSIDataset(NSWVGDataset):
    """
    NSW VG yearly PSI dataset, partitioned by year

    Args:
    ----------
        name (str):
            Dataset name, fixed to "psi_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["year"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        provision_kind (NSWVGProvisionKind):
            Provision kind, fixed to NSWVGProvisionKind.YEAR

    Methods:
    ----------
        run(params: dict | None = None) -> list[BaseAssetfile]:
            `{"mode": "delta"}` (default) loads the provision years without assetfile;
            `{"mode": "full"}` loads every provision year.

    """

    name: ClassVar[str] = "psi_year"
    partitions: ClassVar[list[str]] = ["year"]
    description: ClassVar[str] = "Dataset for NSW VG yearly property sales information."
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    provision_kind: ClassVar[NSWVGProvisionKind] = NSWVGProvisionKind.YEAR
    column_descs: ClassVar[list[ColumnDesc]] = [
        ColumnDesc(
            name="area",
            description="Land area in the unit specified by area_type.",
        ),
        ColumnDesc(
            name="area_type",
            description="Unit of land area. M means square metres and H means hectares.",
        ),
        ColumnDesc(
            name="component_code",
            description="Valuer General valuation grouping code. The archived file specification marks this field for internal use.",
        ),
        ColumnDesc(
            name="contract_date",
            description="Date on which the sale contracts were exchanged.",
        ),
        ColumnDesc(
            name="dealing_number",
            description="Unique identifier for the NSW land dealing recorded on the Notice of Sale. Available in the current file format.",
        ),
        ColumnDesc(
            name="dimensions",
            description="Land parcel dimensions supplied in the archived file format.",
        ),
        ColumnDesc(
            name="district_code",
            description="Three-digit NSW Valuer General district code.",
        ),
        ColumnDesc(
            name="download_time",
            description="Date and time the source file was generated. May be null for archived sales records.",
        ),
        ColumnDesc(
            name="file_name",
            description="Name of the source DAT file.",
        ),
        ColumnDesc(
            name="house_number",
            description="Property street number, including any prefix, suffix, or range.",
        ),
        ColumnDesc(
            name="interest_of_sale",
            description="Percentage of ownership interest associated with the sale, available in the current file format. The source field may be blank for a 100 percent interest. The meaning of zero values in Fortress is unverified.",
        ),
        ColumnDesc(
            name="land_description",
            description="Legal description of the property, typically including lot, section, or plan identifiers. The archived format stores it on the sale record. The current format supplies it in one or more type C records.",
        ),
        ColumnDesc(
            name="locality",
            description="Locality or suburb of the property as recorded in the Register of Land Values.",
        ),
        ColumnDesc(
            name="nature_of_property",
            description="Property classification in the current file format. V means vacant land, R means residence, and 3 means other.",
        ),
        ColumnDesc(
            name="postcode", description="Postal code of the property as recorded in the Register of Land Values."
        ),
        ColumnDesc(
            name="primary_purpose",
            description="Main use of the property, supplied in the current file format for the Other property classification.",
        ),
        ColumnDesc(
            name="property_id", description="Unique identifier for the property in the NSW Register of Land Values."
        ),
        ColumnDesc(
            name="property_name",
            description="Name of the property as recorded in the Register of Land Values. Available in the current file format.",
        ),
        ColumnDesc(
            name="purchase_price",
            description="Purchase price in Australian dollars, sourced from the Notice of Sale.",
        ),
        ColumnDesc(
            name="sale_code",
            description="Sale code supplied in the current file format. The published file specification does not define the individual code values.",
        ),
        ColumnDesc(
            name="sale_counter",
            description="Sale sequence number unique within the source DAT file. Available in the current file format.",
        ),
        ColumnDesc(
            name="settlement_date",
            description="Date on which the sale contract was settled. Available in the current file format.",
        ),
        ColumnDesc(
            name="source",
            description="Internal source code supplied in the archived file format.",
        ),
        ColumnDesc(
            name="strata_lot_number",
            description="Lot identifier for a strata property. Available in the current file format.",
        ),
        ColumnDesc(
            name="street_name",
            description="Property street name, which may include the street type, suffix, and location descriptor.",
        ),
        ColumnDesc(
            name="unit_number",
            description="Property unit number, including any suffix.",
        ),
        ColumnDesc(
            name="valuation_number",
            description="Legacy property valuation number supplied in the archived file format.",
        ),
        ColumnDesc(
            name="year",
            description="Year of the annual download package. Historical archives group sales by registration year. Annual packages in the current format group weekly files by publication year.",
        ),
        ColumnDesc(
            name="zone_code",
            description="Zoning classification code recorded in the Register of Land Values at the time of extraction.",
        ),
    ]
