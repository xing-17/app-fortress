"""
综合测试：destinations.base.destination

覆盖范围
--------
- TestBaseDestination   抽象约束、_resolve_setting、as_dlt_destination、describe
"""

from __future__ import annotations

import json

import pytest

from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.connections.oss.connection import OSSConnection
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.destinations.oss.destination import OSSDestination
from app.common.core.setting import GlobalSetting
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

_DEST_SETTING = BridgesDestinationSetting(
    name="mock_oss",
    connection="mock_conn",
    base_prefix="test/data",
    format="parquet",
)


class _MockBucket:
    def put_object(self, path: str, data) -> None:
        pass

    def get_bucket_info(self) -> dict:
        return {}


class _MockOSSConnection(OSSConnection):
    def __init__(self) -> None:
        BaseConnection.__init__(self, setting=_OSS_CONN_SETTING)
        self.bucket_name = _OSS_CONN_SETTING.bucket
        self.endpoint = _OSS_CONN_SETTING.endpoint
        self._mock_bucket = _MockBucket()

    def _create_connection(self) -> _MockBucket:
        return self._mock_bucket

    def ping(self) -> bool:
        return True


def _make_dest(
    format: str = "parquet",
    base_prefix: str = "test/data",
) -> OSSDestination:
    setting = BridgesDestinationSetting(
        name="mock_oss",
        connection="mock_conn",
        base_prefix=base_prefix,
        format=format,
    )

    class _D(OSSDestination):
        def _resolve_setting(self, name: str) -> BridgesDestinationSetting:
            return setting

    return _D(name="mock_oss", connection=_MockOSSConnection())


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseDestination
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseDestination:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseDestination(name="x", connection=_MockOSSConnection())

    def test_missing_write_raises(self):
        class _NoWrite(BaseDestination):
            def export(self) -> dict:
                return {}

        with pytest.raises(TypeError):
            _NoWrite(name="x", connection=_MockOSSConnection())

    def test_missing_export_raises(self):
        class _NoExport(BaseDestination):
            def write(self, df, table_name, partition_col, partition_prefix) -> None:
                pass

        with pytest.raises(TypeError):
            _NoExport(name="x", connection=_MockOSSConnection())

    def test_resolve_setting_raises_if_not_found(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.bridges, "destinations", [])

        class _D(BaseDestination):
            def write(self, df, table_name, partition_col, partition_prefix) -> None:
                pass

            def export(self) -> dict:
                return {}

        with pytest.raises(KeyError):
            _D(name="nonexistent", connection=_MockOSSConnection())

    def test_log_prefix_uses_subclass_name(self):
        dest = _make_dest()
        # _set_log_prefix uses __class__.__name__, not hardcoded "BaseDestination"
        assert "BaseDestination" not in dest._log_prefix
        assert dest.name in dest._log_prefix

    def test_as_dlt_destination_returns_non_none(self):
        result = _make_dest().as_dlt_destination(
            partition_col="trade_date",
            partition_prefix="date",
        )
        assert result is not None

    def test_describe_returns_valid_json(self):
        parsed = json.loads(_make_dest().describe())
        assert isinstance(parsed, dict)
