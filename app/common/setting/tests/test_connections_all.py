"""
综合测试：app.common.setting.connections

覆盖范围
--------
- TestOssDefaults     各字段默认值正确
- TestOssValidation   必填字段缺失时抛出 ValidationError；自定义值完整存储；name 可选
- TestOssExport       export() 返回完整未脱敏字典
- TestOssDescribe     describe() 返回合法 JSON；敏感字段正确脱敏；非敏感字段值一致
- TestConnectionUnion discriminated union 按 type 正确分发到 OssConnectionSetting
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from app.common.setting.connections import (
    ConnectionSetting,
    OssConnectionSetting,
)

_REQUIRED = dict(
    access_key_id="LTAI5tTEST",
    access_key_secret="SECRET5678",
    endpoint="oss-cn-shanghai.aliyuncs.com",
    region="cn-shanghai",
    bucket="my-test-bucket",
)

_ALL_EXPORT_KEYS = [
    "type",
    "name",
    "access_key_id",
    "access_key_secret",
    "endpoint",
    "region",
    "bucket",
    "url_style",
]


def _make(**kwargs) -> OssConnectionSetting:
    return OssConnectionSetting(**{**_REQUIRED, **kwargs})


# ──────────────────────────────────────────────────────────────────────────────
# TestOssDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestOssDefaults:
    def test_type_default(self):
        assert _make().type == "oss"

    def test_name_default_is_none(self):
        assert _make().name is None

    def test_url_style_default(self):
        assert _make().url_style == "vhost"


# ──────────────────────────────────────────────────────────────────────────────
# TestOssValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestOssValidation:
    def test_missing_access_key_id_raises(self):
        data = {k: v for k, v in _REQUIRED.items() if k != "access_key_id"}
        with pytest.raises(ValidationError):
            OssConnectionSetting(**data)

    def test_missing_access_key_secret_raises(self):
        data = {k: v for k, v in _REQUIRED.items() if k != "access_key_secret"}
        with pytest.raises(ValidationError):
            OssConnectionSetting(**data)

    def test_missing_endpoint_raises(self):
        data = {k: v for k, v in _REQUIRED.items() if k != "endpoint"}
        with pytest.raises(ValidationError):
            OssConnectionSetting(**data)

    def test_missing_region_raises(self):
        data = {k: v for k, v in _REQUIRED.items() if k != "region"}
        with pytest.raises(ValidationError):
            OssConnectionSetting(**data)

    def test_missing_bucket_raises(self):
        data = {k: v for k, v in _REQUIRED.items() if k != "bucket"}
        with pytest.raises(ValidationError):
            OssConnectionSetting(**data)

    def test_name_is_optional(self):
        conn = _make()
        assert conn.name is None

    def test_name_can_be_set(self):
        conn = _make(name="prod")
        assert conn.name == "prod"

    def test_custom_values_stored_correctly(self):
        conn = _make(url_style="path", name="dev")
        assert conn.access_key_id == "LTAI5tTEST"
        assert conn.access_key_secret == "SECRET5678"
        assert conn.endpoint == "oss-cn-shanghai.aliyuncs.com"
        assert conn.region == "cn-shanghai"
        assert conn.bucket == "my-test-bucket"
        assert conn.url_style == "path"
        assert conn.name == "dev"


# ──────────────────────────────────────────────────────────────────────────────
# TestOssExport
# ──────────────────────────────────────────────────────────────────────────────


class TestOssExport:
    def test_export_returns_dict(self):
        assert isinstance(_make().export(), dict)

    def test_export_contains_all_keys(self):
        result = _make().export()
        for key in _ALL_EXPORT_KEYS:
            assert key in result

    def test_export_no_extra_keys(self):
        result = _make().export()
        assert set(result.keys()) == set(_ALL_EXPORT_KEYS)

    def test_export_access_key_id_not_masked(self):
        result = _make().export()
        assert result["access_key_id"] == "LTAI5tTEST"

    def test_export_access_key_secret_not_masked(self):
        result = _make().export()
        assert result["access_key_secret"] == "SECRET5678"

    def test_export_values_match_fields(self):
        conn = _make(name="prod")
        result = conn.export()
        assert result["endpoint"] == conn.endpoint
        assert result["region"] == conn.region
        assert result["bucket"] == conn.bucket
        assert result["url_style"] == conn.url_style
        assert result["name"] == "prod"


# ──────────────────────────────────────────────────────────────────────────────
# TestOssDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestOssDescribe:
    def test_describe_returns_str(self):
        assert isinstance(_make().describe(), str)

    def test_describe_is_valid_json(self):
        result = json.loads(_make().describe())
        assert isinstance(result, dict)

    def test_describe_access_key_id_is_masked(self):
        result = json.loads(_make().describe())
        assert result["access_key_id"].endswith("***")
        assert result["access_key_id"].startswith("LTAI")

    def test_describe_access_key_secret_is_masked(self):
        result = json.loads(_make().describe())
        assert result["access_key_secret"].endswith("***")
        assert result["access_key_secret"].startswith("SECR")

    def test_describe_non_sensitive_values_intact(self):
        conn = _make()
        result = json.loads(conn.describe())
        assert result["endpoint"] == conn.endpoint
        assert result["region"] == conn.region
        assert result["bucket"] == conn.bucket
        assert result["url_style"] == conn.url_style
        assert result["type"] == "oss"


# ──────────────────────────────────────────────────────────────────────────────
# TestConnectionUnion
# ──────────────────────────────────────────────────────────────────────────────


class TestConnectionUnion:
    def test_oss_type_resolves_to_oss_setting(self):
        ta = TypeAdapter(ConnectionSetting)
        result = ta.validate_python({"type": "oss", **_REQUIRED})
        assert isinstance(result, OssConnectionSetting)

    def test_unknown_type_raises(self):
        ta = TypeAdapter(ConnectionSetting)
        with pytest.raises((ValidationError, Exception)):
            ta.validate_python({"type": "unknown", **_REQUIRED})
