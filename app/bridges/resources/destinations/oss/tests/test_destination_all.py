"""
综合测试：destinations.oss.destination

覆盖范围
--------
- TestOSSDestinationInit        属性初始化、log prefix
- TestOSSDestinationFingerprint 确定性、列序无关、数据不同指纹不同
- TestOSSDestinationWrite       partition 校验、路径格式、按分区写出
- TestOSSDestinationWriteFile   parquet/csv 写出、未知格式报错、OSS 失败报错
- TestOSSDestinationExport      export 结构
"""

from __future__ import annotations

import io

import polars as pl
import pytest

from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.connections.oss.connection import OSSConnection
from app.bridges.resources.destinations.oss.destination import OSSDestination
from app.common.setting.bridges import BridgesDestinationSetting
from app.common.setting.connections import OssConnectionSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_OSS_CONN_SETTING = OssConnectionSetting(
    name="mock_conn",
    type="oss",
    access_key_id="ak",
    access_key_secret="sk",
    endpoint="ep.com",
    region="cn",
    bucket="mock-bucket",
)


class _MockBucket:
    """Fake oss2.Bucket：记录 put_object 调用，可配置抛出异常。"""

    def __init__(self, raise_on_put: Exception | None = None) -> None:
        self.put_calls: list[tuple[str, bytes]] = []
        self._raise = raise_on_put

    def put_object(self, path: str, data) -> None:
        if self._raise:
            raise self._raise
        self.put_calls.append((path, data.read()))

    def get_bucket_info(self) -> dict:
        return {}


class _MockOSSConnection(OSSConnection):
    """Test double：绕过 oss2，注入可控的 _MockBucket。"""

    def __init__(self, bucket: _MockBucket | None = None) -> None:
        BaseConnection.__init__(self, setting=_OSS_CONN_SETTING)
        self.bucket_name = _OSS_CONN_SETTING.bucket
        self.endpoint = _OSS_CONN_SETTING.endpoint
        self._mock_bucket = bucket or _MockBucket()

    def _create_connection(self) -> _MockBucket:
        return self._mock_bucket

    def ping(self) -> bool:
        return True

    def get_duckdb_base_location(self) -> str:
        return f"s3://{self.bucket_name}"

    def get_duckdb_base_uri(self) -> str:
        return f"s3://{self.bucket_name}/{_OSS_CONN_SETTING.base_prefix}"


def _make_dest(
    bucket: _MockBucket | None = None,
    format: str = "parquet",
    base_prefix: str = "test/data",
) -> tuple[OSSDestination, _MockBucket]:
    mb = bucket or _MockBucket()
    conn = _MockOSSConnection(mb)
    setting = BridgesDestinationSetting(
        name="mock_oss",
        connection="mock_conn",
        base_prefix=base_prefix,
        format=format,
    )

    class _D(OSSDestination):
        def _resolve_setting(self, name: str) -> BridgesDestinationSetting:
            return setting

    return _D(name="mock_oss", connection=conn), mb


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSDestinationInit
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSDestinationInit:
    def test_name_from_setting(self):
        dest, _ = _make_dest()
        assert dest.name == "mock_oss"

    def test_base_prefix_stripped_of_slashes(self):
        dest, _ = _make_dest(base_prefix=" /leading/trailing/ ")
        assert not dest._base_prefix.startswith("/")
        assert not dest._base_prefix.endswith("/")

    def test_bucket_obtained_from_connection(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        assert dest._bucket is mb

    def test_log_prefix_contains_class_name(self):
        dest, _ = _make_dest()
        # _set_log_prefix in BaseDestination uses __class__.__name__
        assert "BaseDestination" not in dest._log_prefix
        assert dest.name in dest._log_prefix


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSDestinationFingerprint
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSDestinationFingerprint:
    def test_same_data_produces_same_fingerprint(self):
        dest, _ = _make_dest()
        df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        assert dest._get_fingerprint(df) == dest._get_fingerprint(df)

    def test_fingerprint_is_column_order_independent(self):
        dest, _ = _make_dest()
        assert dest._get_fingerprint(pl.DataFrame({"a": [1], "b": [2]})) == dest._get_fingerprint(
            pl.DataFrame({"b": [2], "a": [1]})
        )

    def test_different_data_produces_different_fingerprint(self):
        dest, _ = _make_dest()
        assert dest._get_fingerprint(pl.DataFrame({"a": [1]})) != dest._get_fingerprint(pl.DataFrame({"a": [2]}))

    def test_fingerprint_is_32_hex_chars(self):
        dest, _ = _make_dest()
        fp = dest._get_fingerprint(pl.DataFrame({"x": [1]}))
        assert len(fp) == 32
        assert all(c in "0123456789abcdef" for c in fp)


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSDestinationWrite
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSDestinationWrite:
    def test_missing_partition_col_raises_value_error(self):
        dest, _ = _make_dest()
        with pytest.raises(ValueError, match="Partition column"):
            dest.write_source(pl.DataFrame({"a": [1]}), "tbl", "trade_date", "date")

    def test_writes_one_file_per_unique_partition(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        dest.write_source(
            pl.DataFrame({"trade_date": ["2024-01-01", "2024-01-02"], "v": [1.0, 2.0]}),
            "tbl",
            "trade_date",
            "date",
        )
        assert len(mb.put_calls) == 2

    def test_path_contains_base_prefix(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb, base_prefix="fortress/data")
        dest.write_source(pl.DataFrame({"d": ["2024-01-01"], "v": [1]}), "tbl", "d", "date")
        assert mb.put_calls[0][0].startswith("fortress/data/")

    def test_path_contains_table_name(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        dest.write_source(pl.DataFrame({"d": ["2024-01-01"], "v": [1]}), "my_table", "d", "date")
        assert "/my_table/" in mb.put_calls[0][0]

    def test_path_contains_partition_segment(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        dest.write_source(pl.DataFrame({"d": ["2024-01-05"], "v": [1]}), "tbl", "d", "date")
        assert "/date=2024-01-05/" in mb.put_calls[0][0]

    def test_path_extension_matches_parquet_format(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb, format="parquet")
        dest.write_source(pl.DataFrame({"d": ["2024-01-01"], "v": [1]}), "tbl", "d", "date")
        assert mb.put_calls[0][0].endswith(".parquet")

    def test_path_extension_matches_csv_format(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb, format="csv")
        dest.write_source(pl.DataFrame({"d": ["2024-01-01"], "v": [1]}), "tbl", "d", "date")
        assert mb.put_calls[0][0].endswith(".csv")


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSDestinationWriteFile
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSDestinationWriteFile:
    def test_parquet_bytes_are_valid_parquet(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        df = pl.DataFrame({"x": [1, 2, 3]})
        dest._write_file(df, "p.parquet", fmt="parquet")
        assert pl.read_parquet(io.BytesIO(mb.put_calls[0][1])).equals(df)

    def test_csv_bytes_are_valid_csv(self):
        mb = _MockBucket()
        dest, _ = _make_dest(bucket=mb)
        df = pl.DataFrame({"x": [1, 2], "y": ["a", "b"]})
        dest._write_file(df, "p.csv", fmt="csv")
        assert pl.read_csv(io.BytesIO(mb.put_calls[0][1])).equals(df)

    def test_unsupported_format_raises_value_error(self):
        dest, _ = _make_dest()
        with pytest.raises(ValueError, match="Unsupported format"):
            dest._write_file(pl.DataFrame({"a": [1]}), "p.xyz", fmt="xyz")

    def test_oss_failure_raises_runtime_error(self):
        mb = _MockBucket(raise_on_put=OSError("network error"))
        dest, _ = _make_dest(bucket=mb)
        with pytest.raises(RuntimeError, match="OSS write"):
            dest._write_file(pl.DataFrame({"a": [1]}), "p.parquet", fmt="parquet")


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSDestinationExport
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSDestinationExport:
    def test_export_contains_name(self):
        dest, _ = _make_dest()
        assert dest.export()["name"] == "mock_oss"

    def test_export_type_is_oss(self):
        dest, _ = _make_dest()
        assert dest.export()["type"] == "oss"

    def test_export_contains_bucket(self):
        dest, _ = _make_dest()
        assert dest.export()["bucket"] == "mock-bucket"

    def test_export_contains_base_prefix(self):
        dest, _ = _make_dest(base_prefix="fortress/data")
        assert dest.export()["base_prefix"] == "fortress/data"

    def test_export_contains_format(self):
        dest, _ = _make_dest(format="csv")
        assert dest.export()["format"] == "csv"

    def test_export_contains_connection_info(self):
        dest, _ = _make_dest()
        assert "connection" in dest.export()
