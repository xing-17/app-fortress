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

    def test_missing_complete_rate(self):
        ColumnQuality(
            name="a",
            type="Int64",
        )
        # should raise value error

    @pytest.mark.parametrize("rate", [-0.1, 1.1])
    def test_rate_outside_unit_interval_raises(self, rate):
        with pytest.raises(ValidationError):
            _make_column_quality(complete_rate=rate)


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
            columns=[
                _make_column_quality(name="b"),
                _make_column_quality(name="a"),
            ]
        )
        assert [col.name for col in quality.columns] == ["a", "b"]


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
