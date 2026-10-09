from __future__ import annotations

import hashlib
from io import BytesIO

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

    def test_expression_is_not_evaluated_and_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown column type"):
            IDataframe.resolve_column_type("1 + 1")

    def test_malicious_expression_is_blocked(self):
        with pytest.raises(ValueError, match="Unknown column type"):
            IDataframe.resolve_column_type("__import__('os').system('echo pwned')")


class TestIDataframeInit:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            IDataframe()


class TestIDataframeToParquetBytes:
    def test_returns_bytes_and_sha256_digest(self):
        _df = pl.DataFrame({"a": [1, 2, 3]})
        _data, _digest = IDataframe.to_parquet_bytes(_df)
        assert isinstance(_data, bytes)
        assert _digest == hashlib.sha256(_data).hexdigest()[:32]

    def test_roundtrip_preserves_data(self):
        _df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        _data, _ = IDataframe.to_parquet_bytes(_df)
        _restored = pl.read_parquet(BytesIO(_data))
        assert _restored.equals(_df)

    def test_different_compression_still_roundtrips(self):
        _df = pl.DataFrame({"a": [1, 2, 3]})
        _data, _ = IDataframe.to_parquet_bytes(_df, compression="snappy")
        assert pl.read_parquet(BytesIO(_data)).equals(_df)


# ──────────────────────────────────────────────────────────────────────────────
# TestBenchmark (requires pytest-benchmark)
# ──────────────────────────────────────────────────────────────────────────────
# Run with: pytest app/internal/util/tests/test_dataframe_unit.py::TestBenchmark --benchmark-sort=mean


def _make_wide_rows_df(n_rows: int = 200_000) -> pl.DataFrame:
    _id = pl.int_range(0, n_rows, eager=True)
    return pl.DataFrame(
        {
            "id": _id,
            "category": (_id % 50).cast(pl.Utf8),
            "value": _id.cast(pl.Float64),
        }
    )


def _make_wide_columns_df(n_rows: int = 5_000, n_cols: int = 200) -> pl.DataFrame:
    _id = pl.int_range(0, n_rows, eager=True)
    return pl.DataFrame({f"col_{i}": (_id * i) % (i + 1) for i in range(n_cols)})


class TestBenchmark:
    def test_to_parquet_bytes_throughput_many_rows(self, benchmark):
        _df = _make_wide_rows_df()
        benchmark(IDataframe.to_parquet_bytes, _df)

    def test_to_parquet_bytes_throughput_many_columns(self, benchmark):
        _df = _make_wide_columns_df()
        benchmark(IDataframe.to_parquet_bytes, _df)

    def test_to_parquet_bytes_compression_codec_comparison(self, benchmark):
        _df = _make_wide_rows_df()
        benchmark(IDataframe.to_parquet_bytes, _df, compression="snappy")
