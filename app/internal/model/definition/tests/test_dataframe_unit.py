from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from app.internal.model.definition.dataframe import ColumnDefinition, DataframeDefinition
from app.internal.util.dataframe import IDataframe


class TestColumnDefinition:
    def test_stores_name_and_type(self):
        column = ColumnDefinition(name="age", type="Int64")
        assert column.name == "age"
        assert column.type == "Int64"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            ColumnDefinition(type="Int64")

    def test_missing_type_raises(self):
        with pytest.raises(ValidationError):
            ColumnDefinition(name="age")


class TestDataframeDefinitionDefaults:
    def test_id_has_def_prefix(self):
        definition = DataframeDefinition()
        assert definition.id.startswith("def")

    def test_id_is_unique(self):
        assert DataframeDefinition().id != DataframeDefinition().id

    def test_created_at_is_derived_when_not_provided(self):
        definition = DataframeDefinition()
        assert isinstance(definition.created_at, float)

    def test_created_at_is_preserved_when_provided(self):
        definition = DataframeDefinition(created_at=123.0)
        assert definition.created_at == 123.0

    def test_columns_defaults_to_empty_list(self):
        assert DataframeDefinition().columns == []


class TestDataframeDefinitionDeriveColumns:
    def test_columns_are_sorted_by_name(self):
        definition = DataframeDefinition(
            columns=[
                ColumnDefinition(name="b", type="Int64"),
                ColumnDefinition(name="a", type="Utf8"),
            ]
        )
        assert [col.name for col in definition.columns] == ["a", "b"]


class TestDataframeDefinitionFromDf:
    def test_builds_column_definitions_from_df_columns(self):
        df = pl.DataFrame({"b": [1, 2], "a": ["x", "y"]})
        definition = DataframeDefinition.from_df(df)
        assert [col.name for col in definition.columns] == ["a", "b"]

    def test_column_types_match_stringified_dtype(self):
        df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        definition = DataframeDefinition.from_df(df)
        _by_name = {col.name: col.type for col in definition.columns}
        assert _by_name["a"] == IDataframe.stringify_column_type(df["a"].dtype)
        assert _by_name["b"] == IDataframe.stringify_column_type(df["b"].dtype)

    def test_empty_df_produces_no_columns(self):
        df = pl.DataFrame()
        definition = DataframeDefinition.from_df(df)
        assert definition.columns == []
