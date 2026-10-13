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
    def test_returns_bytes(self):
        _df = pl.DataFrame({"a": [1, 2, 3]})
        _data = IDataframe.to_parquet_bytes(_df)
        assert isinstance(_data, bytes)
        assert _data

    def test_roundtrip_preserves_data(self):
        _df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        _data = IDataframe.to_parquet_bytes(_df)
        _restored = pl.read_parquet(BytesIO(_data))
        assert _restored.equals(_df)

    def test_different_compression_still_roundtrips(self):
        _df = pl.DataFrame({"a": [1, 2, 3]})
        _data = IDataframe.to_parquet_bytes(_df, compression="snappy")
        assert pl.read_parquet(BytesIO(_data)).equals(_df)

    def test_empty_frame_roundtrips(self):
        _df = pl.DataFrame({"a": []}, schema={"a": pl.Int64})
        _data = IDataframe.to_parquet_bytes(_df)
        _restored = pl.read_parquet(BytesIO(_data))
        assert _restored.schema == _df.schema
        assert _restored.height == 0

    def test_custom_metadata_is_written(self):
        _df = pl.DataFrame({"a": [1]})
        _data = IDataframe.to_parquet_bytes(_df, metadata={"k": "v"})
        _plain = IDataframe.to_parquet_bytes(_df)
        assert b"k" in _data and _data != _plain

    def test_same_frame_gives_same_bytes(self):
        _df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        assert IDataframe.to_parquet_bytes(_df) == IDataframe.to_parquet_bytes(_df)


class TestIDataframeToFingerprint:
    def test_default_is_full_sha256_hex(self):
        _data = b"hello"
        assert IDataframe.to_fingerprint(_data) == hashlib.sha256(_data).hexdigest()

    def test_length_truncates_digest(self):
        _data = b"hello"
        _expected = hashlib.sha256(_data).hexdigest()[:32]
        assert IDataframe.to_fingerprint(_data, length=32) == _expected

    def test_length_at_or_above_digest_size_returns_full_digest(self):
        _data = b"hello"
        _full = hashlib.sha256(_data).hexdigest()
        assert IDataframe.to_fingerprint(_data, length=len(_full)) == _full
        assert IDataframe.to_fingerprint(_data, length=1000) == _full

    @pytest.mark.parametrize("length", [0, -1])
    def test_non_positive_length_is_ignored(self, length):
        _data = b"hello"
        assert IDataframe.to_fingerprint(_data, length=length) == hashlib.sha256(_data).hexdigest()

    def test_accepts_memoryview(self):
        _data = b"hello"
        assert IDataframe.to_fingerprint(memoryview(_data)) == IDataframe.to_fingerprint(_data)

    def test_same_bytes_same_fingerprint(self):
        assert IDataframe.to_fingerprint(b"abc") == IDataframe.to_fingerprint(b"abc")

    def test_different_bytes_different_fingerprint(self):
        assert IDataframe.to_fingerprint(b"abc") != IDataframe.to_fingerprint(b"abd")

    def test_empty_bytes_is_valid(self):
        assert IDataframe.to_fingerprint(b"") == hashlib.sha256(b"").hexdigest()


class TestIDataframeParquetFingerprintPipeline:
    def test_frames_differing_only_in_partition_column_get_different_fingerprints(self):
        _a = pl.DataFrame({"d": ["2026-01-01"], "v": [1]})
        _b = pl.DataFrame({"d": ["2026-01-02"], "v": [1]})
        _fa = IDataframe.to_fingerprint(IDataframe.to_parquet_bytes(_a), length=32)
        _fb = IDataframe.to_fingerprint(IDataframe.to_parquet_bytes(_b), length=32)
        assert _fa != _fb

    def test_identical_frames_get_same_fingerprint(self):
        _a = pl.DataFrame({"d": ["2026-01-01"], "v": [1]})
        _b = pl.DataFrame({"d": ["2026-01-01"], "v": [1]})
        _fa = IDataframe.to_fingerprint(IDataframe.to_parquet_bytes(_a), length=32)
        _fb = IDataframe.to_fingerprint(IDataframe.to_parquet_bytes(_b), length=32)
        assert _fa == _fb


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

    def test_to_fingerprint_throughput_on_parquet_bytes(self, benchmark):
        _data = IDataframe.to_parquet_bytes(_make_wide_rows_df())
        benchmark(IDataframe.to_fingerprint, _data, 32)

    def test_to_fingerprint_throughput_on_large_buffer(self, benchmark):
        _data = bytes(64 * 1024 * 1024)
        benchmark(IDataframe.to_fingerprint, _data, 32)

    def test_parquet_then_fingerprint_pipeline(self, benchmark):
        _df = _make_wide_rows_df()

        def _run() -> str:
            return IDataframe.to_fingerprint(IDataframe.to_parquet_bytes(_df), 32)

        benchmark(_run)
