from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.nswvg.dataset import NSWVGDataset
from app.resource.source.nswvg.provision import NSWVGProvisionKind


class WeekPSIDataset(NSWVGDataset):
    """
    NSW VG weekly PSI dataset, partitioned by date

    Shares its schema with `YearPSIDataset`, the date is the Monday the week is published.

    Args:
    ----------
        name (str):
            Dataset name, fixed to "psi_week"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["date"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.WEEK
        provision_kind (NSWVGProvisionKind):
            Provision kind, fixed to NSWVGProvisionKind.WEEK

    Methods:
    ----------
        run(params: dict | None = None) -> list[BaseAssetfile]:
            `{"mode": "delta"}` (default) loads the provision weeks without assetfile;
            `{"mode": "full"}` loads every provision week.

    """

    name: ClassVar[str] = "psi_week"
    partitions: ClassVar[list[str]] = ["date"]
    description: ClassVar[str] = "Dataset for NSW VG weekly property sales information."
    frequency: ClassVar[FrequencyOption] = FrequencyOption.WEEK
    provision_kind: ClassVar[NSWVGProvisionKind] = NSWVGProvisionKind.WEEK
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
            description="Valuer General valuation grouping code.",
        ),
        ColumnDesc(
            name="contract_date",
            description="Date on which the sale contracts were exchanged.",
        ),
        ColumnDesc(
            name="date",
            description="Weekly publication batch date. The batch contains sale records created in the week before the source files were generated.",
        ),
        ColumnDesc(
            name="dealing_number",
            description="Unique identifier for the NSW land dealing recorded on the Notice of Sale.",
        ),
        ColumnDesc(
            name="dimensions",
            description="Land parcel dimensions. This field comes from the archived file format and is generally null in weekly data.",
        ),
        ColumnDesc(
            name="district_code",
            description="Three-digit NSW Valuer General district code.",
        ),
        ColumnDesc(
            name="download_time",
            description="Date and time the source file was generated.",
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
            description="Percentage of ownership interest associated with the sale. The source field may be blank for a 100 percent interest. The meaning of zero values in Fortress is unverified.",
        ),
        ColumnDesc(
            name="land_description",
            description="Legal description of the property, typically including lot, section, or plan identifiers. It comes from one or more type C records.",
        ),
        ColumnDesc(
            name="locality",
            description="Locality or suburb of the property as recorded in the Register of Land Values.",
        ),
        ColumnDesc(
            name="nature_of_property",
            description="Property classification. V means vacant land, R means residence, and 3 means other.",
        ),
        ColumnDesc(
            name="postcode", description="Postal code of the property as recorded in the Register of Land Values."
        ),
        ColumnDesc(
            name="primary_purpose",
            description="Main use of the property, supplied for the Other property classification.",
        ),
        ColumnDesc(
            name="property_id",
            description="Unique identifier for the property in the NSW Register of Land Values.",
        ),
        ColumnDesc(
            name="property_name",
            description="Name of the property as recorded in the Register of Land Values.",
        ),
        ColumnDesc(
            name="purchase_price",
            description="Purchase price in Australian dollars, sourced from the Notice of Sale.",
        ),
        ColumnDesc(
            name="sale_code",
            description="Sale code supplied in the source file. The published file specification does not define the individual code values.",
        ),
        ColumnDesc(
            name="sale_counter",
            description="Sale sequence number unique within the source DAT file.",
        ),
        ColumnDesc(
            name="settlement_date",
            description="Date on which the sale contract was settled.",
        ),
        ColumnDesc(
            name="source",
            description="Internal source code from the archived file format. This field is generally null in weekly data.",
        ),
        ColumnDesc(
            name="strata_lot_number",
            description="Lot identifier for a strata property.",
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
            description="Legacy property valuation number from the archived file format. This field is generally null in weekly data.",
        ),
        ColumnDesc(
            name="zone_code",
            description="Zoning classification code recorded in the Register of Land Values at the time of extraction.",
        ),
    ]
