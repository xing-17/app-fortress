"""
综合测试：app.common.setting.cache

覆盖范围
--------
- TestDefaults    各字段默认值正确
- TestValidation  自定义值完整存储；chunksize 可选
- TestExport      export() 返回完整字典且结构正确
- TestDescribe    describe() 返回合法 JSON；值与模型一致
"""

from __future__ import annotations

import json

from app.common.setting.cache import CacheSetting

_ALL_KEYS = [
    "path",
    "ttl_hours",
]


# ──────────────────────────────────────────────────────────────────────────────
# TestDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_name_default(self):
        assert CacheSetting().name == "cache"

    def test_url_default(self):
        assert CacheSetting().path == ".cache/bridges/cache.duckdb"


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_custom_name_stored(self):
        assert CacheSetting(name="my-cache").name == "my-cache"

    def test_custom_path_stored(self):
        path = "custom/path/cache.duckdb"
        assert CacheSetting(path=path).path == path

    def test_custom_ttl_hours_stored(self):
        assert CacheSetting(ttl_hours=72).ttl_hours == 72

    def test_all_custom_values_stored_correctly(self):
        setting = CacheSetting(name="prod-cache", path="sqlite:///tmp/prod.db", ttl_hours=1000)
        assert setting.name == "prod-cache"
        assert setting.path == "sqlite:///tmp/prod.db"
        assert setting.ttl_hours == 1000


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        assert isinstance(CacheSetting().export(), dict)

    def test_export_contains_all_keys(self):
        result = CacheSetting().export()
        for key in _ALL_KEYS:
            assert key in result

    def test_export_values_match_fields(self):
        setting = CacheSetting(name="test", ttl_hours=200)
        result = setting.export()
        assert result["name"] == "test"
        assert result["path"] == setting.path
        assert result["ttl_hours"] == 200


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_str(self):
        assert isinstance(CacheSetting().describe(), str)

    def test_describe_is_valid_json(self):
        result = json.loads(CacheSetting().describe())
        assert isinstance(result, dict)

    def test_describe_values_match_export(self):
        setting = CacheSetting(name="check", ttl_hours=100)
        parsed = json.loads(setting.describe())
        exported = setting.export()
        assert parsed["name"] == exported["name"]
        assert parsed["path"] == exported["path"]
        assert parsed["ttl_hours"] == exported["ttl_hours"]
