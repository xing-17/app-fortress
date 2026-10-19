from __future__ import annotations

import polars as pl
import pytest

from app.resource.source.nswvg.provision import (
    PSI_COLUMNS,
    NSWVGProvisionItem,
    NSWVGProvisionKind,
)
from app.resource.source.nswvg.tests.conftest import (
    archive_b,
    dat,
    make_item,
    modern_b,
    modern_c,
    zip_bytes,
)


class TestItemDerivation:
    def test_four_digit_key_is_year(self, provision_root):
        _item = NSWVGProvisionItem(path=make_item(provision_root, "1995"))
        assert _item.kind == NSWVGProvisionKind.YEAR
        assert _item.partitions == {"year": "1995"}

    def test_eight_digit_key_is_week_with_iso_date(self, provision_root):
        _item = NSWVGProvisionItem(path=make_item(provision_root, "20260105"))
        assert _item.kind == NSWVGProvisionKind.WEEK
        assert _item.partitions == {"date": "2026-01-05"}

    def test_unknown_key_raises(self, provision_root):
        with pytest.raises(ValueError, match="Cannot derive kind"):
            NSWVGProvisionItem(path=make_item(provision_root, "abc"))

    def test_invalid_week_date_raises(self, provision_root):
        with pytest.raises(ValueError):
            NSWVGProvisionItem(path=make_item(provision_root, "20269999"))

    def test_missing_directory_raises(self, provision_root):
        with pytest.raises(ValueError, match="not a directory"):
            NSWVGProvisionItem(path=provision_root / "1995")

    def test_file_path_raises(self, provision_root):
        provision_root.mkdir()
        (provision_root / "1995").write_text("x")
        with pytest.raises(ValueError, match="not a directory"):
            NSWVGProvisionItem(path=provision_root / "1995")

    def test_explicit_kind_and_partitions_are_kept(self, provision_root):
        _item = NSWVGProvisionItem(
            path=make_item(provision_root, "anything"),
            kind=NSWVGProvisionKind.YEAR,
            partitions={"year": "2000"},
        )
        assert _item.partitions == {"year": "2000"}


class TestItemLoad:
    def test_empty_directory_raises(self, provision_root):
        _item = NSWVGProvisionItem(path=make_item(provision_root, "1995"))
        with pytest.raises(ValueError, match="No .DAT found"):
            _item.load()

    def test_read_loads_implicitly_and_raises_when_empty(self, provision_root):
        _item = NSWVGProvisionItem(path=make_item(provision_root, "1995"))
        with pytest.raises(ValueError, match="No .DAT found"):
            _item.read()

    def test_non_dat_files_are_ignored(self, provision_root):
        _dir = make_item(provision_root, "1995", {"readme.txt": b"x"})
        with pytest.raises(ValueError, match="No .DAT found"):
            NSWVGProvisionItem(path=_dir).load()

    def test_load_returns_self(self, provision_root):
        _dir = make_item(provision_root, "20260105", {"a.DAT": dat(modern_b())})
        _item = NSWVGProvisionItem(path=_dir)
        assert _item.load() is _item


class TestItemPackaging:
    def test_loose_dat_uppercase_and_lowercase(self, provision_root):
        _dir = make_item(
            provision_root,
            "20260105",
            {
                "a.DAT": dat(modern_b(property_id="1")),
                "b.dat": dat(modern_b(property_id="2")),
            },
        )
        _df = NSWVGProvisionItem(path=_dir).read()
        assert sorted(_df["property_id"].to_list()) == ["1", "2"]

    def test_nested_subfolder(self, provision_root):
        _dir = make_item(provision_root, "20260105")
        (_dir / "sub" / "deep").mkdir(parents=True)
        (_dir / "sub" / "deep" / "a.DAT").write_bytes(dat(modern_b()))
        assert NSWVGProvisionItem(path=_dir).read().height == 1

    def test_zip(self, provision_root):
        _dir = make_item(
            provision_root,
            "20260105",
            {"w.zip": zip_bytes({"a.DAT": dat(modern_b(property_id="1")), "b.DAT": dat(modern_b(property_id="2"))})},
        )
        assert NSWVGProvisionItem(path=_dir).read().height == 2

    def test_zip_inside_zip(self, provision_root):
        _inner = zip_bytes({"a.DAT": dat(modern_b())})
        _dir = make_item(provision_root, "20260105", {"w.zip": zip_bytes({"inner.zip": _inner})})
        assert NSWVGProvisionItem(path=_dir).read().height == 1

    def test_zip_entry_in_folder_is_read(self, provision_root):
        _dir = make_item(provision_root, "20260105", {"w.zip": zip_bytes({"folder/a.DAT": dat(modern_b())})})
        _df = NSWVGProvisionItem(path=_dir).read()
        assert _df["file_name"].to_list() == ["a.DAT"]

    def test_hidden_and_macosx_entries_are_skipped(self, provision_root):
        _dir = make_item(
            provision_root,
            "20260105",
            {
                "a.DAT": dat(modern_b(property_id="1")),
                ".hidden.DAT": dat(modern_b(property_id="2")),
                "w.zip": zip_bytes(
                    {
                        "__MACOSX/b.DAT": dat(modern_b(property_id="3")),
                        "._c.DAT": dat(modern_b(property_id="4")),
                    }
                ),
            },
        )
        (_dir / "__MACOSX").mkdir()
        (_dir / "__MACOSX" / "d.DAT").write_bytes(dat(modern_b(property_id="5")))
        assert NSWVGProvisionItem(path=_dir).read()["property_id"].to_list() == ["1"]


class TestItemRead:
    def test_schema_is_all_string_columns_plus_partitions(self, provision_root):
        _dir = make_item(provision_root, "20260105", {"a.DAT": dat(modern_b())})
        _df = NSWVGProvisionItem(path=_dir).read()
        assert _df.columns == [*PSI_COLUMNS, "date"]
        assert set(_df.schema.values()) == {pl.String}
        assert _df["date"].to_list() == ["2026-01-05"]

    def test_year_partition_column(self, provision_root):
        _dir = make_item(provision_root, "1995", {"a.DAT": dat(archive_b())})
        assert NSWVGProvisionItem(path=_dir).read()["year"].to_list() == ["1995"]

    def test_dat_without_sales_gives_empty_frame(self, provision_root):
        _dir = make_item(provision_root, "20260105", {"a.DAT": dat()})
        _df = NSWVGProvisionItem(path=_dir).read()
        assert _df.is_empty()
        assert _df.columns == [*PSI_COLUMNS, "date"]

    def test_file_name_is_the_dat_name(self, provision_root):
        _dir = make_item(provision_root, "20260105", {"001_SALES_DATA.DAT": dat(modern_b())})
        assert NSWVGProvisionItem(path=_dir).read()["file_name"].to_list() == ["001_SALES_DATA.DAT"]


class TestParseDat:
    @pytest.fixture
    def item(self, provision_root):
        return NSWVGProvisionItem(path=make_item(provision_root, "20260105"))

    def test_modern_row_maps_columns(self, item):
        _rows = item.parse_dat("a.DAT", dat(modern_b()))
        assert len(_rows) == 1
        _row = dict(zip(PSI_COLUMNS, _rows[0]))
        assert _row["district_code"] == "001"
        assert _row["property_id"] == "100"
        assert _row["sale_counter"] == "1"
        assert _row["download_time"] == "20260105 09:30"
        assert _row["property_name"] is None
        assert _row["unit_number"] == "U1"
        assert _row["street_name"] == "MAIN ST"
        assert _row["area"] == "600.5"
        assert _row["contract_date"] == "20260102"
        assert _row["settlement_date"] == "20260103"
        assert _row["purchase_price"] == "500000"
        assert _row["zone_code"] == "R2"
        assert _row["dealing_number"] == "AB123"
        assert _row["source"] is None
        assert _row["valuation_number"] is None
        assert _row["file_name"] == "a.DAT"

    def test_archive_row_maps_columns_and_converts_date(self, item):
        _rows = item.parse_dat("y.DAT", dat(archive_b()))
        _row = dict(zip(PSI_COLUMNS, _rows[0]))
        assert _row["district_code"] == "001"
        assert _row["source"] == "RP"
        assert _row["valuation_number"] == "V1"
        assert _row["property_id"] == "100"
        assert _row["contract_date"] == "19950102"
        assert _row["purchase_price"] == "250000"
        assert _row["land_description"] == "LOT 1 DP 9"
        assert _row["sale_counter"] is None
        assert _row["settlement_date"] is None

    def test_every_row_has_one_value_per_column(self, item):
        _rows = item.parse_dat("a.DAT", dat(modern_b()))
        _rows += item.parse_dat("y.DAT", dat(archive_b()))
        assert {len(_r) for _r in _rows} == {len(PSI_COLUMNS)}

    def test_c_records_are_joined_into_land_description(self, item):
        _rows = item.parse_dat(
            "a.DAT",
            dat(modern_b(), modern_c(land="LOT 1"), modern_c(land="LOT 2")),
        )
        assert dict(zip(PSI_COLUMNS, _rows[0]))["land_description"] == "LOT 1; LOT 2"

    def test_c_record_only_matches_its_own_sale(self, item):
        _rows = item.parse_dat(
            "a.DAT",
            dat(
                modern_b(property_id="100", counter="1"),
                modern_b(property_id="100", counter="2"),
                modern_c(property_id="100", counter="2", land="LOT 9"),
            ),
        )
        _lands = [dict(zip(PSI_COLUMNS, _r))["land_description"] for _r in _rows]
        assert _lands == [None, "LOT 9"]

    def test_c_record_without_land_is_ignored(self, item):
        _rows = item.parse_dat("a.DAT", dat(modern_b(), modern_c(land="")))
        assert dict(zip(PSI_COLUMNS, _rows[0]))["land_description"] is None

    def test_b_record_with_unexpected_field_count_raises(self, item):
        with pytest.raises(ValueError, match="unexpected B record"):
            item.parse_dat("bad.DAT", dat("B;001;100"))

    def test_a_d_z_records_are_skipped(self, item):
        assert item.parse_dat("a.DAT", dat("D;001;100;1;P;V")) == []

    def test_crlf_and_lf_line_endings(self, item):
        _lf = "\n".join([modern_b(property_id="1"), modern_b(property_id="2")]).encode()
        assert len(item.parse_dat("a.DAT", _lf)) == 2

    def test_latin1_fallback(self, item):
        _line = modern_b().replace("MAIN ST", "RUE CAF\u00c9").encode("latin-1")
        _rows = item.parse_dat("a.DAT", _line)
        assert dict(zip(PSI_COLUMNS, _rows[0]))["street_name"] == "RUE CAF\u00c9"

    def test_empty_values_become_none(self, item):
        _rows = item.parse_dat("a.DAT", dat(modern_b(settlement_date="")))
        assert dict(zip(PSI_COLUMNS, _rows[0]))["settlement_date"] is None


class TestDmyToYmd:
    @pytest.fixture
    def item(self, provision_root):
        return NSWVGProvisionItem(path=make_item(provision_root, "1995"))

    def test_none_stays_none(self, item):
        assert item._dmy_to_ymd(None) is None

    def test_pads_day_and_month(self, item):
        assert item._dmy_to_ymd("2/1/1995") == "19950102"

    def test_unmatched_value_is_returned_as_is(self, item):
        assert item._dmy_to_ymd("19950102") == "19950102"
