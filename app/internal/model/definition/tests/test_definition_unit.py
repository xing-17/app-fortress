from __future__ import annotations

import hashlib
import json

import polars as pl

from app.internal.model.definition.dataframe import (
    ColumnDefinition,
    DataframeDefinition,
)


def _fingerprint(columns: dict[str, str]) -> str:
    _string = json.dumps(columns, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(_string.encode("utf-8")).hexdigest()


class TestDataframeDefinitionDerivedFields:
    def test_created_at_is_filled_when_missing(self):
        result = DataframeDefinition()
        assert isinstance(result.created_at, float)
        assert result.created_at > 0

    def test_created_at_is_kept_when_provided(self):
        result = DataframeDefinition(created_at=123.0)
        assert result.created_at == 123.0

    def test_columns_are_sorted_by_name(self):
        result = DataframeDefinition(
            columns=[
                ColumnDefinition(name="b", type="Int64"),
                ColumnDefinition(name="a", type="String"),
            ]
        )
        assert [c.name for c in result.columns] == ["a", "b"]

    def test_fingerprint_matches_expected_hash(self):
        result = DataframeDefinition(
            columns=[
                ColumnDefinition(name="a", type="Int64"),
                ColumnDefinition(name="b", type="String"),
            ]
        )
        assert result.fingerprint == _fingerprint({"a": "Int64", "b": "String"})

    def test_fingerprint_is_independent_of_column_order(self):
        first = DataframeDefinition(
            columns=[
                ColumnDefinition(name="a", type="Int64"),
                ColumnDefinition(name="b", type="String"),
            ]
        )
        second = DataframeDefinition(
            columns=[
                ColumnDefinition(name="b", type="String"),
                ColumnDefinition(name="a", type="Int64"),
            ]
        )
        assert first.fingerprint == second.fingerprint

    def test_fingerprint_changes_with_column_type(self):
        first = DataframeDefinition(columns=[ColumnDefinition(name="a", type="Int64")])
        second = DataframeDefinition(columns=[ColumnDefinition(name="a", type="String")])
        assert first.fingerprint != second.fingerprint

    def test_explicit_fingerprint_is_kept(self):
        result = DataframeDefinition(fingerprint="custom")
        assert result.fingerprint == "custom"

    def test_empty_columns_still_have_fingerprint(self):
        result = DataframeDefinition()
        assert result.fingerprint == _fingerprint({})


class TestDataframeDefinitionFromFrame:
    def test_builds_columns_from_frame(self):
        df = pl.DataFrame({"b": [1, 2], "a": ["x", "y"]})
        result = DataframeDefinition.from_frame(df)
        assert [c.name for c in result.columns] == ["a", "b"]
        assert all(isinstance(c, ColumnDefinition) for c in result.columns)
        assert all(c.type for c in result.columns)

    def test_same_schema_yields_same_fingerprint(self):
        first = DataframeDefinition.from_frame(pl.DataFrame({"a": [1], "b": ["x"]}))
        second = DataframeDefinition.from_frame(pl.DataFrame({"b": ["y", "z"], "a": [2, 3]}))
        assert first.fingerprint == second.fingerprint

    def test_different_dtype_yields_different_fingerprint(self):
        first = DataframeDefinition.from_frame(pl.DataFrame({"a": [1]}))
        second = DataframeDefinition.from_frame(pl.DataFrame({"a": [1.0]}))
        assert first.fingerprint != second.fingerprint

    def test_empty_frame_has_no_columns(self):
        result = DataframeDefinition.from_frame(pl.DataFrame())
        assert result.columns == []
