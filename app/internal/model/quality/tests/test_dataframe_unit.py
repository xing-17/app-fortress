from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from app.internal.model.quality.dataframe import ColumnQuality, DataframeQuality
from app.internal.util.dataframe import IDataframe


def _make_column_quality(**overrides) -> ColumnQuality:
    kwargs = dict(
        name="a",
        type="Int64",
        complete_count=4,
        complete_rate=1.0,
        null_count=0,
        null_rate=0.0,
        unique_count=3,
        unique_rate=0.75,
        duplicate_count=1,
        duplicate_rate=0.25,
    )
    kwargs.update(overrides)
    return ColumnQuality(**kwargs)


class TestColumnQuality:
    def test_stores_provided_fields(self):
        column = _make_column_quality()
        assert column.name == "a"
        assert column.complete_count == 4
        assert column.unique_rate == 0.75

    def test_counts_default_to_zero(self):
        column = ColumnQuality(
            name="a",
            type="Int64",
            complete_rate=1.0,
            null_rate=0.0,
            unique_rate=1.0,
            duplicate_rate=0.0,
        )
        assert column.complete_count == 0
        assert column.null_count == 0
        assert column.unique_count == 0
        assert column.duplicate_count == 0

    def test_rates_default_to_zero(self):
        column = ColumnQuality(name="a", type="Int64")
        assert column.complete_rate == 0.0
        assert column.null_rate == 0.0
        assert column.unique_rate == 0.0
        assert column.duplicate_rate == 0.0

    @pytest.mark.parametrize("rate", [-0.1, 1.1])
    def test_rate_outside_unit_interval_raises(self, rate):
        with pytest.raises(ValidationError):
            _make_column_quality(complete_rate=rate)


class TestColumnQualityValidateRatePairs:
    def test_complete_and_null_rate_must_sum_to_zero_or_one(self):
        with pytest.raises(ValidationError):
            _make_column_quality(complete_rate=0.5, null_rate=0.2)

    def test_unique_and_duplicate_rate_must_sum_to_zero_or_one(self):
        with pytest.raises(ValidationError):
            _make_column_quality(unique_rate=0.5, duplicate_rate=0.2)

    def test_both_zero_is_allowed_as_no_data_placeholder(self):
        column = ColumnQuality(name="a", type="Int64")
        assert column.complete_rate + column.null_rate == 0.0
        assert column.unique_rate + column.duplicate_rate == 0.0


class TestColumnQualityDeriveFlags:
    def test_is_constant_true_when_single_distinct_value(self):
        column = _make_column_quality(unique_count=1, duplicate_count=3, unique_rate=0.25, duplicate_rate=0.75)
        assert column.is_constant is True

    def test_is_constant_false_when_multiple_distinct_values(self):
        assert _make_column_quality().is_constant is False

    def test_is_all_null_true_when_fully_null(self):
        column = _make_column_quality(
            complete_count=0,
            complete_rate=0.0,
            null_count=4,
            null_rate=1.0,
            unique_count=0,
            unique_rate=0.0,
            duplicate_count=0,
            duplicate_rate=0.0,
        )
        assert column.is_all_null is True

    def test_is_all_null_false_when_partially_populated(self):
        assert _make_column_quality().is_all_null is False

    def test_is_unique_true_when_no_nulls_and_fully_distinct(self):
        column = _make_column_quality(
            complete_count=4,
            complete_rate=1.0,
            null_count=0,
            null_rate=0.0,
            unique_count=4,
            unique_rate=1.0,
            duplicate_count=0,
            duplicate_rate=0.0,
        )
        assert column.is_unique is True

    def test_is_unique_false_when_duplicates_present(self):
        assert _make_column_quality().is_unique is False

    def test_is_unique_false_when_nulls_present(self):
        column = _make_column_quality(
            complete_count=3,
            complete_rate=0.75,
            null_count=1,
            null_rate=0.25,
            unique_count=3,
            unique_rate=1.0,
            duplicate_count=0,
            duplicate_rate=0.0,
        )
        assert column.is_unique is False


class TestDataframeQualityDefaults:
    def test_id_has_quality_prefix(self):
        assert DataframeQuality().id.startswith("quality")

    def test_width_and_height_default_to_zero(self):
        quality = DataframeQuality()
        assert quality.width == 0
        assert quality.height == 0

    def test_created_at_is_derived_when_not_provided(self):
        assert isinstance(DataframeQuality().created_at, float)

    def test_created_at_is_preserved_when_provided(self):
        assert DataframeQuality(created_at=123.0).created_at == 123.0

    def test_columns_defaults_to_empty_list(self):
        assert DataframeQuality().columns == []


class TestDataframeQualityDeriveIsEmpty:
    def test_zero_height_is_empty(self):
        assert DataframeQuality(width=5, height=0).is_empty is True

    def test_zero_width_is_empty(self):
        assert DataframeQuality(width=0, height=5).is_empty is True

    def test_positive_width_and_height_is_not_empty(self):
        assert DataframeQuality(width=5, height=5).is_empty is False


class TestDataframeQualityDeriveColumns:
    def test_columns_are_sorted_by_name(self):
        quality = DataframeQuality(
            width=2,
            columns=[
                _make_column_quality(name="b"),
                _make_column_quality(name="a"),
            ],
        )
        assert [col.name for col in quality.columns] == ["a", "b"]


class TestDataframeQualityValidateRowsWithinHeight:
    def test_complete_rows_exceeding_height_raises(self):
        with pytest.raises(ValidationError):
            DataframeQuality(height=2, complete_rows=3)

    def test_duplicate_rows_exceeding_height_raises(self):
        with pytest.raises(ValidationError):
            DataframeQuality(height=2, duplicate_rows=3)


class TestDataframeQualityValidateColumnsMatchWidth:
    def test_columns_length_mismatching_width_raises(self):
        with pytest.raises(ValidationError):
            DataframeQuality(width=2, columns=[_make_column_quality(name="a")])

    def test_empty_columns_does_not_require_matching_width(self):
        assert DataframeQuality(width=3).columns == []


class TestDataframeQualityFromDf:
    def test_computes_dataframe_level_metrics(self):
        df = pl.DataFrame({"a": [1, 1, 2, 3], "b": ["x", "x", "y", "z"]})
        quality = DataframeQuality.from_df(df)
        assert quality.width == 2
        assert quality.height == 4
        assert quality.is_empty is False
        assert quality.complete_rows == 4
        assert quality.duplicate_rows == 2

    def test_computes_column_level_metrics(self):
        df = pl.DataFrame({"a": [1, 1, 2, 3], "b": ["x", "x", "y", "z"]})
        quality = DataframeQuality.from_df(df)
        _by_name = {col.name: col for col in quality.columns}

        assert _by_name["a"].type == IDataframe.stringify_column_type(df["a"].dtype)
        assert _by_name["a"].complete_count == 4
        assert _by_name["a"].complete_rate == 1.0
        assert _by_name["a"].null_count == 0
        assert _by_name["a"].null_rate == 0.0
        assert _by_name["a"].unique_count == 3
        assert _by_name["a"].unique_rate == 0.75
        assert _by_name["a"].duplicate_count == 1
        assert _by_name["a"].duplicate_rate == 0.25

    def test_columns_are_sorted_by_name(self):
        df = pl.DataFrame({"b": [1, 2], "a": [3, 4]})
        quality = DataframeQuality.from_df(df)
        assert [col.name for col in quality.columns] == ["a", "b"]

    def test_accounts_for_null_values(self):
        df = pl.DataFrame({"a": [1, None, 2, 2]})
        quality = DataframeQuality.from_df(df)
        _col = quality.columns[0]
        assert _col.complete_count == 3
        assert _col.complete_rate == 0.75
        assert _col.null_count == 1
        assert _col.null_rate == 0.25

    def test_fully_empty_df_has_no_columns(self):
        quality = DataframeQuality.from_df(pl.DataFrame())
        assert quality.width == 0
        assert quality.height == 0
        assert quality.is_empty is True
        assert quality.columns == []

    def test_zero_row_df_with_columns_has_zeroed_rates(self):
        df = pl.DataFrame({"a": [], "b": []})
        quality = DataframeQuality.from_df(df)
        assert quality.is_empty is True
        for col in quality.columns:
            assert col.complete_rate == 0.0
            assert col.null_rate == 0.0
            assert col.unique_rate == 0.0
            assert col.duplicate_rate == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# TestBenchmark (requires pytest-benchmark)
# ──────────────────────────────────────────────────────────────────────────────
# Run with: pytest app/internal/model/quality/tests/test_dataframe_unit.py::TestBenchmark --benchmark-sort=mean


def _make_wide_rows_df(n_rows: int = 200_000) -> pl.DataFrame:
    _id = pl.int_range(0, n_rows, eager=True)
    return pl.DataFrame(
        {
            "id": _id,
            "category": (_id % 50).cast(pl.Utf8),
            "value": _id.cast(pl.Float64),
        }
    ).with_columns(pl.when(pl.col("id") % 11 == 0).then(None).otherwise(pl.col("value")).alias("value"))


def _make_wide_columns_df(n_rows: int = 5_000, n_cols: int = 200) -> pl.DataFrame:
    _id = pl.int_range(0, n_rows, eager=True)
    return pl.DataFrame({f"col_{i}": (_id * i) % (i + 1) for i in range(n_cols)})


class TestBenchmark:
    def test_from_df_throughput_many_rows(self, benchmark):
        df = _make_wide_rows_df()
        benchmark(DataframeQuality.from_df, df)

    def test_from_df_throughput_many_columns(self, benchmark):
        df = _make_wide_columns_df()
        benchmark(DataframeQuality.from_df, df)
