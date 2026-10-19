from __future__ import annotations

import io

import polars as pl
import pytest

from app.resource.source.nswvg.dataset import NSWVGRunMode
from app.resource.source.nswvg.datasets.psi_week import WeekPSIDataset
from app.resource.source.nswvg.datasets.psi_year import YearPSIDataset
from app.resource.source.nswvg.tests.conftest import archive_b, dat, make_item, modern_b


@pytest.fixture
def week(provision_root, vault, store, log_stream):
    return WeekPSIDataset(
        provision_path=provision_root / "psi_week",
        asset=vault.asset(rel="psi_week", filekind=WeekPSIDataset.filekind, partitions=WeekPSIDataset.partitions),
        database=store.database("psi_week"),
        log_stream=log_stream,
        tags={},
        _authorized=True,
    )


@pytest.fixture
def year(provision_root, vault, store, log_stream):
    return YearPSIDataset(
        provision_path=provision_root / "psi_year",
        asset=vault.asset(rel="psi_year", filekind=YearPSIDataset.filekind, partitions=YearPSIDataset.partitions),
        database=store.database("psi_year"),
        log_stream=log_stream,
        tags={},
        _authorized=True,
    )


def _add_week(dataset, key: str, **kwargs) -> None:
    make_item(dataset.provision_path, key, {"a.DAT": dat(modern_b(**kwargs))})


def _warnings(log_stream) -> list[str]:
    return [_r.getMessage() for _r in log_stream.collector.records if _r.levelname == "WARNING"]


class TestProvisionPath:
    def test_directory_is_created(self, week):
        assert week.provision_path.is_dir()

    def test_relative_and_user_paths_are_resolved(self, week):
        assert week.provision_path.is_absolute()


class TestListProvisionItems:
    def test_items_are_sorted_by_key(self, week):
        _add_week(week, "20260112")
        _add_week(week, "20260105")
        assert [_i.key for _i in week.list_provision_items()] == ["20260105", "20260112"]

    def test_plain_files_are_ignored(self, week):
        (week.provision_path / ".DS_Store").write_text("x")
        assert week.list_provision_items() == []

    def test_invalid_directory_is_skipped_with_warning(self, week, log_stream):
        make_item(week.provision_path, "notakey")
        assert week.list_provision_items() == []
        assert any("notakey" in _m for _m in _warnings(log_stream))

    def test_other_kind_is_skipped_with_warning(self, week, log_stream):
        make_item(week.provision_path, "1995")
        assert week.list_provision_items() == []
        assert any("1995" in _m for _m in _warnings(log_stream))


class TestParseMode:
    def test_none_is_delta(self, week):
        assert week._parse_mode(None) == NSWVGRunMode.DELTA

    def test_string_is_case_insensitive(self, week):
        assert week._parse_mode("FULL") == NSWVGRunMode.FULL

    def test_enum_passes_through(self, week):
        assert week._parse_mode(NSWVGRunMode.FULL) == NSWVGRunMode.FULL

    def test_unknown_mode_raises(self, week):
        with pytest.raises(ValueError, match="Unknown run mode"):
            week._parse_mode("incremental")


class TestDiscover:
    def test_full_returns_all_items(self, week):
        _add_week(week, "20260105")
        _add_week(week, "20260112")
        assert len(week.discover(NSWVGRunMode.FULL)) == 2

    def test_delta_without_assetfiles_returns_all_items(self, week):
        _add_week(week, "20260105")
        assert len(week.discover()) == 1

    def test_delta_excludes_written_items(self, week):
        _add_week(week, "20260105")
        _add_week(week, "20260112")
        week.write(week.transform(week.extract({"key": "20260105"})))
        assert [_i.key for _i in week.discover()] == ["20260112"]

    def test_delta_with_nothing_new_is_empty(self, week):
        _add_week(week, "20260105")
        week.run()
        assert week.discover() == []


class TestExtract:
    def test_reads_the_named_item(self, week):
        _add_week(week, "20260105", property_id="7")
        _df = week.extract({"key": "20260105"})
        assert _df["property_id"].to_list() == ["7"]
        assert _df["date"].to_list() == ["2026-01-05"]

    @pytest.mark.parametrize("params", [None, {}, {"key": ""}, {"key": "../x"}, {"key": "a/b"}])
    def test_invalid_key_raises(self, week, params):
        with pytest.raises(ValueError, match="Param 'key'"):
            week.extract(params)

    def test_missing_item_raises(self, week):
        with pytest.raises(ValueError, match="not a directory"):
            week.extract({"key": "20260105"})


class TestTransform:
    def _raw(self, week, **kwargs) -> pl.DataFrame:
        _add_week(week, "20260105", **kwargs)
        return week.extract({"key": "20260105"})

    def test_casts_types(self, week):
        _df = week.transform(self._raw(week))
        assert _df.schema["sale_counter"] == pl.Int32
        assert _df.schema["download_time"] == pl.Datetime("us")
        assert _df.schema["area"] == pl.Float64
        assert _df.schema["purchase_price"] == pl.Float64
        assert _df.schema["interest_of_sale"] == pl.Float64
        assert _df.schema["contract_date"] == pl.Date
        assert _df.schema["settlement_date"] == pl.Date
        assert _df["contract_date"][0].isoformat() == "2026-01-02"
        assert _df["purchase_price"][0] == 500000.0

    def test_unparsable_value_becomes_null_with_warning(self, week, log_stream):
        _df = week.transform(self._raw(week, price="N/A"))
        assert _df["purchase_price"][0] is None
        assert any("purchase_price" in _m for _m in _warnings(log_stream))

    def test_clean_data_logs_no_warning(self, week, log_stream):
        week.transform(self._raw(week))
        assert _warnings(log_stream) == []

    def test_archive_date_is_parsed(self, year):
        make_item(year.provision_path, "1995", {"a.DAT": dat(archive_b())})
        _df = year.transform(year.extract({"key": "1995"}))
        assert _df["contract_date"][0].isoformat() == "1995-01-02"


class TestWrite:
    def test_empty_frame_writes_nothing(self, week):
        assert week.write(pl.DataFrame()) == []

    def test_missing_partition_column_raises(self, week):
        with pytest.raises(ValueError, match="partition columns"):
            week.write(pl.DataFrame({"id": [1]}))

    def test_one_assetfile_per_partition_value(self, week):
        _df = pl.DataFrame({"id": [1, 2, 3], "date": ["2026-01-05", "2026-01-12", "2026-01-05"]})
        _files = week.write(_df)
        assert sorted(_f.partitions["date"] for _f in _files) == ["2026-01-05", "2026-01-12"]
        _frames = {_f.partitions["date"]: pl.read_parquet(io.BytesIO(_f.read_bytes())) for _f in _files}
        assert _frames["2026-01-05"]["id"].to_list() == [1, 3]

    def test_is_idempotent_and_writes_metadata(self, week):
        _df = pl.DataFrame({"id": [1], "date": ["2026-01-05"]})
        _first = week.write(_df)[0]
        _second = week.write(_df)[0]
        assert _first.name == _second.name
        assert len(week.list_assetfiles()) == 1
        assert week.read_metadata(_first).export()


class TestRun:
    def test_delta_is_the_default_and_second_run_is_a_noop(self, week):
        _add_week(week, "20260105")
        assert len(week.run()) == 1
        assert week.run() == []

    def test_delta_only_processes_new_items(self, week):
        _add_week(week, "20260105")
        week.run()
        _add_week(week, "20260112")
        _files = week.run({"mode": "delta"})
        assert [_f.partitions["date"] for _f in _files] == ["2026-01-12"]

    def test_full_reprocesses_everything(self, week):
        _add_week(week, "20260105")
        _add_week(week, "20260112")
        week.run()
        assert len(week.run({"mode": "full"})) == 2

    def test_no_items_returns_empty_and_logs(self, week, log_stream):
        assert week.run() == []
        assert any("No items discovered" in _r.getMessage() for _r in log_stream.collector.records)

    def test_unknown_mode_raises(self, week):
        with pytest.raises(ValueError, match="Unknown run mode"):
            week.run({"mode": "nope"})

    def test_failure_keeps_files_already_written(self, week):
        _add_week(week, "20260105")
        make_item(week.provision_path, "20260112", {"bad.DAT": dat("B;001;100")})
        with pytest.raises(ValueError, match="unexpected B record"):
            week.run()
        assert [_f.partitions["date"] for _f in week.list_assetfiles()] == ["2026-01-05"]

    def test_year_dataset_partitions_by_year(self, year):
        make_item(year.provision_path, "1995", {"a.DAT": dat(archive_b())})
        _files = year.run()
        assert [_f.partitions for _f in _files] == [{"year": "1995"}]
        _df = pl.read_parquet(io.BytesIO(_files[0].read_bytes()))
        assert _df["contract_date"][0].isoformat() == "1995-01-02"
