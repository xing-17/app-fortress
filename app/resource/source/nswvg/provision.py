from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Callable, Iterator
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import polars as pl
from pydantic import Field, PrivateAttr, model_validator

from app.internal.abstract.domain import IAbstractDomain

# Output columns in order; the raw frame is all String
PSI_COLUMNS: list[str] = [
    "district_code",
    "source",
    "valuation_number",
    "property_id",
    "sale_counter",
    "download_time",
    "property_name",
    "unit_number",
    "house_number",
    "street_name",
    "locality",
    "postcode",
    "area",
    "area_type",
    "dimensions",
    "contract_date",
    "settlement_date",
    "purchase_price",
    "zone_code",
    "nature_of_property",
    "primary_purpose",
    "strata_lot_number",
    "component_code",
    "sale_code",
    "interest_of_sale",
    "dealing_number",
    "land_description",
    "file_name",
]

# Number of `;`-split fields of a B record
# trailing empty field included.
_ARCHIVE_B_FIELDS: int = 22
_MODERN_B_FIELDS: int = 25
_MODERN_C_FIELDS: int = 7
_DMY: re.Pattern = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


class NSWVGProvisionKind(StrEnum):
    """
    Provision kind of an NSW VG dataset.

    Members:
    -----------
        WEEK:
            Weekly provision.
        YEAR:
            Yearly provision.

    """

    WEEK = "week"
    YEAR = "year"


class NSWVGProvisionItem(IAbstractDomain):
    """
    One provision directory (a week or a year) holding PSI .DAT files in any packaging

    Loose .DAT, nested subfolders and zips (also zips inside zips) are all flattened,
    the .DAT layout (archive or modern) is resolved per file by `parse_dat`.

    Attributes:
    ----------
        key (str):
            Directory name, 4 digits for a year (YYYY) or 8 digits for a week (YYYYMMDD)

    Args:
    ----------
        path (Path):
            Provision directory, must exist
        partitions (dict[str, str] | None):
            Partitions of the item, derived from the key when omitted
            (`year` for a year, `date` as YYYY-MM-DD for a week)
        kind (NSWVGProvisionKind | None):
            Provision kind, derived from the key when omitted

    Methods:
    ----------
        load() -> NSWVGProvisionItem:
            Ensure at least one .DAT exists, raise ValueError otherwise.
        read() -> pl.DataFrame:
            Parse every .DAT into one all-String frame of `PSI_COLUMNS` plus the partition columns.
        parse_dat(name: str, data: bytes) -> list[tuple]:
            Parse one .DAT into sale rows, A/D/Z records are skipped.

    """

    path: Path = Field(
        ...,
        description="[Required] The path of the provision item.",
    )
    partitions: dict[str, str] | None = Field(
        default=None,
        description="[Optional] The partitions of the provision item.",
    )
    kind: NSWVGProvisionKind | None = Field(
        default=None,
        description="[Optional] The kind of the provision item.",
    )

    # Private attributes
    _loaded: bool = PrivateAttr(default=False)

    @model_validator(mode="after")
    def _derive_path(self) -> "NSWVGProvisionItem":
        _path: Path = self.path.expanduser().resolve()
        if not _path.is_dir():
            raise ValueError(f"Provision path '{_path}' is not a directory.")
        object.__setattr__(self, "path", _path)
        return self

    @model_validator(mode="after")
    def _derive_kind(self) -> "NSWVGProvisionItem":
        if self.kind is None:
            if re.fullmatch(r"\d{4}", self.key):
                _kind = NSWVGProvisionKind.YEAR
            elif re.fullmatch(r"\d{8}", self.key):
                _kind = NSWVGProvisionKind.WEEK
            else:
                raise ValueError(f"Cannot derive kind from '{self.key}'.")
            object.__setattr__(self, "kind", _kind)
        return self

    @model_validator(mode="after")
    def _derive_partitions(self) -> "NSWVGProvisionItem":
        if not self.partitions:
            if self.kind == NSWVGProvisionKind.YEAR:
                _ptns = {"year": self.key}
            elif self.kind == NSWVGProvisionKind.WEEK:
                _dt = datetime.strptime(self.key, "%Y%m%d")
                _ptns = {"date": _dt.strftime("%Y-%m-%d")}
            else:
                raise ValueError(f"Cannot derive partitions from '{self.key}'.")
            object.__setattr__(self, "partitions", _ptns)
        return self

    @property
    def key(self) -> str:
        return self.path.name

    def load(self) -> "NSWVGProvisionItem":
        if next(self._iter_dats(), None) is None:
            raise ValueError(f"No .DAT found under '{self.path}'.")
        self._loaded = True
        return self

    def read(self) -> pl.DataFrame:
        if not self._loaded:
            self.load()
        _rows: list[tuple] = []
        for _name, _read in self._iter_dats():
            _parsed = self.parse_dat(_name, _read())
            _rows.extend(_parsed)
        _df: pl.DataFrame = pl.DataFrame(
            _rows,
            schema={_c: pl.String for _c in PSI_COLUMNS},
            orient="row",
        )
        _extra_cols: dict[str, str] = dict(self.partitions or {})

        return _df.with_columns(
            *[pl.lit(_v).alias(_k) for _k, _v in _extra_cols.items()],
        )

    def _iter_dats(self) -> Iterator[tuple[str, Callable[[], bytes]]]:
        for _p in sorted(self.path.rglob("*")):
            if _p.is_file():
                if not _p.name.startswith(".") and "__MACOSX" not in _p.parts:
                    yield from self._iter_entry(_p.name, _p.read_bytes)

    def _iter_entry(
        self,
        name: str,
        read: Callable[[], bytes],
    ) -> Iterator[tuple[str, Callable[[], bytes]]]:
        # `read` is lazy and must be called before the generator advances
        # (zip is closed after the with block)
        _lower: str = name.lower()
        if _lower.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(read())) as _zf:
                for _info in _zf.infolist():
                    _base: str = _info.filename.rsplit("/", 1)[-1]
                    if _info.is_dir() or _base.startswith(".") or _info.filename.startswith("__MACOSX/"):
                        continue
                    yield from self._iter_entry(
                        _base,
                        lambda _i=_info: _zf.read(_i),
                    )
        elif _lower.endswith(".dat"):
            yield name, read

    def _dmy_to_ymd(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        _match = _DMY.fullmatch(value)
        if _match is None:
            return value
        _d, _m, _y = _match.groups()
        return f"{_y}{int(_m):02d}{int(_d):02d}"

    def _archive_row(
        self,
        t: list[str | None],
        file_name: str,
    ) -> tuple:
        # B;district;source;valuation no;property id;unit;house;street;locality;postcode;
        #   contract date (dd/mm/yyyy);price;land description;area;area type;dimensions;component;zone;...
        return (
            t[1], t[2], t[3], t[4], None, None,
            None, t[5], t[6], t[7], t[8], t[9],
            t[13], t[14], t[15], self._dmy_to_ymd(t[10]), None, t[11],
            t[17], None, None, None,
            t[16], None, None, None, t[12], file_name,
        )  # fmt: skip

    def _modern_row(
        self,
        t: list[str | None],
        land_description: str | None,
        file_name: str,
    ) -> tuple:
        # B;district;property id;sale counter;download time;name;unit;house;street;locality;postcode;
        #   area;area type;contract date;settlement date;price;zone;nature;purpose;strata lot;
        #   component;sale code;interest;dealing no;
        return (
            t[1], None, None, t[2], t[3], t[4],
            t[5], t[6], t[7], t[8], t[9], t[10],
            t[11], t[12], None, t[13], t[14], t[15],
            t[16], t[17], t[18], t[19],
            t[20], t[21], t[22], t[23], land_description, file_name,
        )  # fmt: skip

    def parse_dat(
        self,
        name: str,
        data: bytes,
    ) -> list[tuple]:
        # Parse one .DAT into sale rows
        # archive (1990~2001) and modern layouts alike
        # A/D/Z are skipped.
        _sales: list[list[str | None]] = []
        _lands: dict[tuple, list[str]] = {}

        # Decode the raw data into a string
        # trying UTF-8 first
        # falling back to Latin-1
        try:
            _data = data.decode("utf-8")
        except UnicodeDecodeError:
            _data = data.decode("latin-1")

        # Split the decoded data into lines and process each line.
        for _line in _data.split("\n"):
            _line = _line.rstrip("\r")
            _kind: str = _line[:2]
            if _kind == "B;":
                # Process an archive B record.
                _t: list[str | None] = [_v or None for _v in _line.split(";")]
                if len(_t) not in (_ARCHIVE_B_FIELDS, _MODERN_B_FIELDS):
                    raise ValueError(f"{name}: unexpected B record with {len(_t)} fields")
                _sales.append(_t)
            elif _kind == "C;":
                _t = [_v or None for _v in _line.split(";")]
                # A few 2001 rows lack the sale counter cannot be matched to a sale
                if len(_t) == _MODERN_C_FIELDS and _t[5]:
                    _lands.setdefault((_t[1], _t[2], _t[3]), []).append(_t[5])

        _rows: list[tuple] = []
        for _t in _sales:
            if len(_t) == _ARCHIVE_B_FIELDS:
                _rows.append(self._archive_row(_t, name))
            else:
                _land: list[str] = _lands.get((_t[1], _t[2], _t[3]), [])
                _land_description = "; ".join(_land) or None
                _rows.append(self._modern_row(_t, _land_description, name))
        return _rows
