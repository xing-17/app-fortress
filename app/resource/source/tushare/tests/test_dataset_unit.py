from __future__ import annotations

import io
from typing import ClassVar

import polars as pl
import pytest

from app.resource.accessory.paginate.paginate import Paginate
from app.resource.source.tushare.dataset import TushareDataset


class DemoDataset(TushareDataset):
    name: ClassVar[str] = "demo"
    partitions: ClassVar[list[str]] = ["part"]
    method: ClassVar[str] = "demo"
    paginate: ClassVar[Paginate] = Paginate(page_size=2, end_page=5)

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        return df


@pytest.fixture
def dataset(session, vault, store, log_stream):
    return DemoDataset(
        session=session,
        asset=vault.asset(rel="demo", filekind=DemoDataset.filekind, partitions=DemoDataset.partitions),
        database=store.database("demo"),
        log_stream=log_stream,
        tags={},
        _authorized=True,
    )


class TestDatasetCall:
    def test_single_short_page_stops_after_one_call(self, dataset, api):
        api.rows = [(1, "a")]
        _df = dataset.extract()
        assert _df.height == 1
        assert len(api.calls) == 1

    def test_pages_are_concatenated_until_a_short_page(self, dataset, api):
        api.rows = [(i, "a") for i in range(5)]
        _df = dataset.extract()
        assert _df["id"].to_list() == [0, 1, 2, 3, 4]
        assert [(c["limit"], c["offset"]) for c in api.calls] == [(2, 0), (2, 2), (2, 4)]

    def test_exact_multiple_of_page_size_ends_on_empty_page(self, dataset, api):
        api.rows = [(i, "a") for i in range(4)]
        _df = dataset.extract()
        assert _df.height == 4
        assert len(api.calls) == 3

    def test_stops_at_end_page(self, dataset, api):
        api.rows = [(i, "a") for i in range(100)]
        _df = dataset.extract()
        assert _df.height == 10  # page_size 2 * end_page 5
        assert len(api.calls) == 5

    def test_empty_result_is_an_empty_frame(self, dataset, api):
        _df = dataset.extract()
        assert _df.is_empty()

    def test_params_are_forwarded_without_mutating_the_caller_dict(self, dataset, api):
        api.rows = [(1, "a")]
        _params = {"ts_code": "000001.SZ"}
        dataset.extract(params=_params)
        assert api.calls[0]["ts_code"] == "000001.SZ"
        assert _params == {"ts_code": "000001.SZ"}

    def test_unknown_method_raises(self, dataset):
        with pytest.raises(ValueError, match="not found"):
            dataset.call("no_such_method", {})


class TestDatasetRetry:
    def test_transient_error_is_retried(self, dataset, api):
        api.rows = [(1, "a")]
        api.fail_times = 1
        assert dataset.extract().height == 1
        assert len(api.calls) == 2

    def test_persistent_error_is_raised_after_retries(self, dataset, api):
        api.fail_times = 99
        with pytest.raises(Exception, match="boom"):
            dataset.extract()
        assert len(api.calls) == 4  # first call + max_retries(3)


class TestDatasetWrite:
    def test_empty_frame_writes_nothing(self, dataset):
        assert dataset.write(pl.DataFrame()) == []

    def test_missing_partition_column_raises(self, dataset):
        with pytest.raises(ValueError, match="partition columns"):
            dataset.write(pl.DataFrame({"id": [1]}))

    def test_one_assetfile_per_partition_value(self, dataset):
        _df = pl.DataFrame({"id": [1, 2, 3], "part": ["a", "b", "a"]})
        _files = dataset.write(_df)
        assert len(_files) == 2
        _frames = {f.partitions["part"]: pl.read_parquet(io.BytesIO(f.read_bytes())) for f in _files}
        assert _frames["a"]["id"].to_list() == [1, 3]
        assert _frames["b"]["id"].to_list() == [2]

    def test_filename_is_content_fingerprint_and_idempotent(self, dataset):
        _df = pl.DataFrame({"id": [1], "part": ["a"]})
        _first = dataset.write(_df)[0]
        _second = dataset.write(_df)[0]
        assert _first.name == _second.name
        assert _first.name.endswith(".parquet")
        assert len(dataset.list_assetfiles()) == 1

    def test_metadata_is_written_for_each_assetfile(self, dataset):
        _files = dataset.write(pl.DataFrame({"id": [1, 2], "part": ["a", "b"]}))
        for _file in _files:
            assert dataset.read_metadata(_file).export()

    def test_run_extracts_transforms_and_writes(self, dataset, api):
        api.rows = [(1, "a"), (2, "b"), (3, "a")]
        _files = dataset.run()
        assert len(_files) == 2


class TestColumnHelpers:
    def test_format_date_value_parses_yyyymmdd(self, dataset):
        _df = dataset._col_format_date_value(pl.DataFrame({"d": ["20240102"]}), cols=["d", "absent"])
        assert _df.schema["d"] == pl.Date
        assert _df["d"][0].isoformat() == "2024-01-02"

    def test_ensure_bool_casts_int_flags(self, dataset):
        _df = dataset._col_ensure_bool_columns(pl.DataFrame({"f": [0, 1]}), cols=["f"])
        assert _df["f"].to_list() == [False, True]

    def test_ensure_float_casts_ints(self, dataset):
        _df = dataset._col_ensure_float_columns(pl.DataFrame({"x": [1, 2]}), cols=["x"])
        assert _df.schema["x"] == pl.Float64

    def test_add_snapshotdate_adds_one_constant_column(self, dataset):
        _df = dataset._col_add_snapshotdate(pl.DataFrame({"x": [1, 2]}))
        assert _df["snapshotdate"].n_unique() == 1

    def test_add_snapshotdate_keeps_empty_frame_empty(self, dataset):
        assert dataset._col_add_snapshotdate(pl.DataFrame()).is_empty()
