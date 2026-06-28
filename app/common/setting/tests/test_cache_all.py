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
    "name",
    "url",
    "chunksize",
]


# ──────────────────────────────────────────────────────────────────────────────
# TestDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_name_default(self):
        assert CacheSetting().name == "cache"

    def test_url_default(self):
        assert CacheSetting().url == "sqlite:///cache/system/cache.db"

    def test_chunksize_default_is_none(self):
        assert CacheSetting().chunksize is None


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_custom_name_stored(self):
        assert CacheSetting(name="my-cache").name == "my-cache"

    def test_custom_url_stored(self):
        url = "postgresql://user:pass@localhost:5432/mydb"
        assert CacheSetting(url=url).url == url

    def test_custom_chunksize_stored(self):
        assert CacheSetting(chunksize=500).chunksize == 500

    def test_chunksize_is_optional(self):
        setting = CacheSetting()
        assert setting.chunksize is None

    def test_all_custom_values_stored_correctly(self):
        setting = CacheSetting(
            name="prod-cache",
            url="sqlite:///tmp/prod.db",
            chunksize=1000,
        )
        assert setting.name == "prod-cache"
        assert setting.url == "sqlite:///tmp/prod.db"
        assert setting.chunksize == 1000


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

    def test_export_no_extra_keys(self):
        result = CacheSetting().export()
        assert set(result.keys()) == set(_ALL_KEYS)

    def test_export_values_match_fields(self):
        setting = CacheSetting(name="test", chunksize=200)
        result = setting.export()
        assert result["name"] == "test"
        assert result["url"] == setting.url
        assert result["chunksize"] == 200

    def test_export_chunksize_none_included(self):
        result = CacheSetting().export()
        assert result["chunksize"] is None


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
        setting = CacheSetting(name="check", chunksize=100)
        parsed = json.loads(setting.describe())
        exported = setting.export()
        assert parsed["name"] == exported["name"]
        assert parsed["url"] == exported["url"]
        assert parsed["chunksize"] == exported["chunksize"]
