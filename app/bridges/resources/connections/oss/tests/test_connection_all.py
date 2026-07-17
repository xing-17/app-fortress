"""
综合测试：connections.oss.connection

覆盖范围
--------
- TestOSSConnection   属性初始化、_create_connection（mock oss2）、ping、get_duckdb_secret、export
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.bridges.resources.connections.oss.connection import OSSConnection
from app.bridges.resources.secret.duckdb import SecretDuckdb
from app.common.setting.connections import OssConnectionSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_OSS_SETTING = OssConnectionSetting(
    name="test_conn",
    type="oss",
    access_key_id="test_access_key",
    access_key_secret="test_secret_key",
    endpoint="oss-cn-test.aliyuncs.com",
    region="cn-test",
    bucket="test-bucket",
)


def _make_conn(monkeypatch=None, bucket=None) -> OSSConnection:
    """返回 OSSConnection，可选 mock oss2.Bucket。"""
    conn = OSSConnection(setting=_OSS_SETTING)
    if monkeypatch is not None and bucket is not None:
        import oss2

        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", lambda **kw: bucket)

    return conn


# ──────────────────────────────────────────────────────────────────────────────
# TestOSSConnection
# ──────────────────────────────────────────────────────────────────────────────


class TestOSSConnection:
    # ── init ─────────────────────────────────────────────────────────────────

    def test_name_from_setting(self):
        assert OSSConnection(setting=_OSS_SETTING).name == "test_conn"

    def test_type_from_setting(self):
        assert OSSConnection(setting=_OSS_SETTING).type == "oss"

    def test_bucket_name_from_setting(self):
        assert OSSConnection(setting=_OSS_SETTING).bucket_name == "test-bucket"

    def test_endpoint_from_setting(self):
        assert OSSConnection(setting=_OSS_SETTING).endpoint == "oss-cn-test.aliyuncs.com"

    def test_region_from_setting(self):
        assert OSSConnection(setting=_OSS_SETTING).region == "cn-test"

    def test_not_connected_on_init(self):
        assert OSSConnection(setting=_OSS_SETTING).is_connected is False

    # ── _create_connection ───────────────────────────────────────────────────

    def test_create_connection_returns_oss_bucket(self, monkeypatch):
        import oss2

        mock_bucket = MagicMock(spec=oss2.Bucket)
        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", lambda **kw: mock_bucket)
        conn = OSSConnection(setting=_OSS_SETTING)
        assert conn.get_connection() is mock_bucket

    def test_create_connection_does_not_pass_region_to_bucket(self, monkeypatch):
        """oss2.Bucket does not accept a region kwarg — verify it isn't passed."""
        import oss2

        captured: dict = {}

        def _capture_bucket(**kw):
            captured.update(kw)
            return MagicMock(spec=oss2.Bucket)

        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", _capture_bucket)
        OSSConnection(setting=_OSS_SETTING).get_connection()
        assert "region" not in captured

    def test_create_connection_passes_endpoint(self, monkeypatch):
        import oss2

        captured: dict = {}

        def _capture_bucket(**kw):
            captured.update(kw)
            return MagicMock(spec=oss2.Bucket)

        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", _capture_bucket)
        OSSConnection(setting=_OSS_SETTING).get_connection()
        assert captured.get("endpoint") == "oss-cn-test.aliyuncs.com"

    def test_create_connection_passes_bucket_name(self, monkeypatch):
        import oss2

        captured: dict = {}

        def _capture_bucket(**kw):
            captured.update(kw)
            return MagicMock(spec=oss2.Bucket)

        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", _capture_bucket)
        OSSConnection(setting=_OSS_SETTING).get_connection()
        assert captured.get("bucket_name") == "test-bucket"

    # ── ping ─────────────────────────────────────────────────────────────────

    def test_ping_returns_true_on_success(self, monkeypatch):
        import oss2

        mock_bucket = MagicMock(spec=oss2.Bucket)
        mock_bucket.get_bucket_info.return_value = {}
        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", lambda **kw: mock_bucket)
        assert OSSConnection(setting=_OSS_SETTING).ping() is True

    def test_ping_returns_false_on_exception(self, monkeypatch):
        import oss2

        mock_bucket = MagicMock(spec=oss2.Bucket)
        mock_bucket.get_bucket_info.side_effect = Exception("connection refused")
        monkeypatch.setattr(oss2, "Auth", lambda **kw: MagicMock())
        monkeypatch.setattr(oss2, "Bucket", lambda **kw: mock_bucket)
        assert OSSConnection(setting=_OSS_SETTING).ping() is False

    # ── export ───────────────────────────────────────────────────────────────

    def test_export_contains_name(self):
        assert OSSConnection(setting=_OSS_SETTING).export()["name"] == "test_conn"

    def test_export_contains_type(self):
        assert OSSConnection(setting=_OSS_SETTING).export()["type"] == "oss"

    def test_export_contains_bucket(self):
        assert OSSConnection(setting=_OSS_SETTING).export()["bucket"] == "test-bucket"

    def test_export_contains_endpoint(self):
        assert OSSConnection(setting=_OSS_SETTING).export()["endpoint"] == "oss-cn-test.aliyuncs.com"

    def test_export_does_not_contain_credentials(self):
        exported = OSSConnection(setting=_OSS_SETTING).export()
        assert "access_key_id" not in exported
        assert "access_key_secret" not in exported

    # ── get_duckdb_secret ────────────────────────────────────────────────────

    def test_get_duckdb_secret_returns_secret_duckdb(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert isinstance(secret, SecretDuckdb)

    def test_get_duckdb_secret_name_includes_connection_name(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.name == "_oss_conn_secret_test_conn"

    def test_get_duckdb_secret_type_is_s3(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.type == "s3"

    def test_get_duckdb_secret_scope_includes_bucket(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.scope == "s3://test-bucket"

    def test_get_duckdb_secret_params_contains_key_id(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.params["KEY_ID"] == "test_access_key"

    def test_get_duckdb_secret_params_contains_secret(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.params["SECRET"] == "test_secret_key"

    def test_get_duckdb_secret_params_contains_region(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.params["REGION"] == "cn-test"

    def test_get_duckdb_secret_params_contains_endpoint(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert secret.config.params["ENDPOINT"] == "oss-cn-test.aliyuncs.com"

    def test_get_duckdb_secret_params_contains_url_style(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert "URL_STYLE" in secret.config.params

    def test_get_duckdb_secret_params_contains_use_ssl(self):
        conn = OSSConnection(setting=_OSS_SETTING)
        secret = conn.get_duckdb_secret()
        assert "USE_SSL" in secret.config.params
