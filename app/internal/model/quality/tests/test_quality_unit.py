from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from app.internal.model.quality.dataframe import ColumnQuality, DataframeQuality


class TestColumnQualityValidation:
    def test_defaults_are_valid(self):
        result = ColumnQuality(name="a", type="Int64")
        assert result.complete_count == 0
        assert result.is_all_null is False

    def test_complete_and_null_rate_must_sum_to_one_or_zero(self):
        with pytest.raises(ValidationError):
            ColumnQuality(name="a", type="Int64", complete_rate=0.5, null_rate=0.2)

    def test_unique_and_duplicate_rate_must_sum_to_one_or_zero(self):
        with pytest.raises(ValidationError):
            ColumnQuality(name="a", type="Int64", unique_rate=0.5, duplicate_rate=0.2)

    def test_rate_out_of_range_is_rejected(self):
        with pytest.raises(ValidationError):
            ColumnQuality(name="a", type="Int64", complete_rate=1.5, null_rate=-0.5)

    def test_negative_count_is_rejected(self):
        with pytest.raises(ValidationError):
            ColumnQuality(name="a", type="Int64", null_count=-1)


class TestColumnQualityFlags:
    def test_is_constant_when_single_unique_value(self):
        result = ColumnQuality(name="a", type="Int64", unique_count=1)
        assert result.is_constant is True

    def test_is_not_constant_with_multiple_unique_values(self):
        result = ColumnQuality(name="a", type="Int64", unique_count=2)
        assert result.is_constant is False

    def test_is_all_null(self):
        result = ColumnQuality(name="a", type="Int64", complete_count=0, null_count=3, null_rate=1.0)
        assert result.is_all_null is True

    def test_is_not_all_null_when_values_exist(self):
        result = ColumnQuality(name="a", type="Int64", complete_count=1, complete_rate=1.0)
        assert result.is_all_null is False

    def test_is_unique(self):
        result = ColumnQuality(
            name="a", type="Int64", complete_count=3, complete_rate=1.0, unique_count=3, unique_rate=1.0
        )
        assert result.is_unique is True

    def test_is_not_unique_when_nulls_present(self):
        result = ColumnQuality(
            name="a",
            type="Int64",
            complete_count=2,
            complete_rate=0.5,
            null_count=2,
            null_rate=0.5,
            unique_count=4,
            unique_rate=1.0,
        )
        assert result.is_unique is False

    def test_flags_are_rederived_over_supplied_values(self):
        result = ColumnQuality(name="a", type="Int64", is_constant=True, is_unique=True)
        assert result.is_constant is False
        assert result.is_unique is False


class TestDataframeQualityDerivedFields:
    def test_is_empty_when_no_rows(self):
        assert DataframeQuality(width=2, height=0).is_empty is True

    def test_is_empty_when_no_columns(self):
        assert DataframeQuality(width=0, height=2).is_empty is True

    def test_is_not_empty_with_rows_and_columns(self):
        assert DataframeQuality(width=1, height=1, is_empty=True).is_empty is False

    def test_created_at_is_filled_when_missing(self):
        result = DataframeQuality()
        assert isinstance(result.created_at, float)
        assert result.created_at > 0

    def test_created_at_is_kept_when_provided(self):
        assert DataframeQuality(created_at=42.0).created_at == 42.0

    def test_columns_are_sorted_by_name(self):
        result = DataframeQuality(
            width=2,
            height=1,
            columns=[ColumnQuality(name="b", type="Int64"), ColumnQuality(name="a", type="Int64")],
        )
        assert [c.name for c in result.columns] == ["a", "b"]


class TestDataframeQualityValidation:
    def test_complete_rows_cannot_exceed_height(self):
        with pytest.raises(ValidationError):
            DataframeQuality(width=1, height=1, complete_rows=2)

    def test_duplicate_rows_cannot_exceed_height(self):
        with pytest.raises(ValidationError):
            DataframeQuality(width=1, height=1, duplicate_rows=2)

    def test_columns_length_must_match_width(self):
        with pytest.raises(ValidationError):
            DataframeQuality(width=2, height=1, columns=[ColumnQuality(name="a", type="Int64")])

    def test_empty_columns_allowed_with_any_width(self):
        assert DataframeQuality(width=3, height=1).columns == []


class TestDataframeQualityFromFrame:
    def test_basic_frame_metrics(self):
        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "x", None]})
        result = DataframeQuality.from_frame(df)
        assert result.width == 2
        assert result.height == 3
        assert result.is_empty is False
        assert result.complete_rows == 2
        assert result.duplicate_rows == 0

        col_a, col_b = result.columns
        assert col_a.name == "a"
        assert col_a.complete_count == 3
        assert col_a.null_count == 0
        assert col_a.unique_count == 3
        assert col_a.duplicate_count == 0
        assert col_a.is_unique is True
        assert col_b.name == "b"
        assert col_b.complete_count == 2
        assert col_b.null_count == 1
        assert col_b.complete_rate == pytest.approx(2 / 3)
        assert col_b.null_rate == pytest.approx(1 / 3)
        assert col_b.unique_count == 2
        assert col_b.duplicate_count == 1
        assert col_b.is_unique is False

    def test_duplicate_rows_are_counted(self):
        df = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        result = DataframeQuality.from_frame(df)
        assert result.duplicate_rows == 2

    def test_constant_column(self):
        result = DataframeQuality.from_frame(pl.DataFrame({"a": [5, 5, 5]}))
        assert result.columns[0].is_constant is True

    def test_all_null_column(self):
        df = pl.DataFrame({"a": [None, None]}, schema={"a": pl.Int64})
        result = DataframeQuality.from_frame(df)
        assert result.complete_rows == 0
        assert result.columns[0].is_all_null is True

    def test_frame_with_no_rows_has_placeholder_columns(self):
        df = pl.DataFrame(schema={"a": pl.Int64, "b": pl.String})
        result = DataframeQuality.from_frame(df)
        assert result.width == 2
        assert result.height == 0
        assert result.is_empty is True
        assert [c.name for c in result.columns] == ["a", "b"]
        assert all(c.complete_count == 0 and c.null_count == 0 for c in result.columns)

    def test_frame_with_no_columns(self):
        result = DataframeQuality.from_frame(pl.DataFrame())
        assert result.width == 0
        assert result.is_empty is True
        assert result.columns == []
