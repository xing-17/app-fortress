from __future__ import annotations

import polars as pl
import pytest

from app.internal.util.dataframe import IDataframe


class TestIDataframeDatatypeNamespace:
    def test_contains_known_dtype_names(self):
        _namespace = IDataframe._datatype_namespace()
        assert "Int64" in _namespace
        assert "String" in _namespace
        assert _namespace["Int64"] is pl.Int64

    def test_all_values_are_polars_datatype_subclasses(self):
        _namespace = IDataframe._datatype_namespace()
        assert _namespace
        for _obj in _namespace.values():
            assert isinstance(_obj, type)
            assert issubclass(_obj, pl.DataType)


class TestIDataframeStringifyColumnType:
    def test_stringifies_simple_type(self):
        assert IDataframe.stringify_column_type(pl.Int64()) == "Int64"

    def test_stringifies_parametric_type(self):
        assert IDataframe.stringify_column_type(pl.List(pl.Int64())) == str(pl.List(pl.Int64()))


class TestIDataframeResolveColumnType:
    def test_resolves_simple_type_name(self):
        _result = IDataframe.resolve_column_type("Int64")
        assert _result == pl.Int64()

    def test_resolves_string_alias(self):
        _result = IDataframe.resolve_column_type("Utf8")
        assert _result == pl.String()

    def test_unknown_name_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown column type"):
            IDataframe.resolve_column_type("NotARealType")

    def test_non_datatype_expression_raises_value_error(self):
        with pytest.raises(ValueError, match="Not a polars DataType"):
            IDataframe.resolve_column_type("1 + 1")

    def test_malicious_expression_is_blocked(self):
        with pytest.raises(ValueError, match="Unknown column type"):
            IDataframe.resolve_column_type("__import__('os').system('echo pwned')")


class TestIDataframeInit:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            IDataframe()
