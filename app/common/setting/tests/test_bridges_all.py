"""
综合测试：app.common.setting.providers

覆盖范围
--------
- TestBridgesCacheSetting 默认值正确；自定义值存储；export() 结构完整
- TestTushareDefaults     各字段默认值正确
- TestTushareValidation   secret 必填；缺失时抛 ValidationError；自定义值完整存储
- TestTushareExport       export() 返回完整未脱敏字典；包含全部字段
- TestProviderUnion       discriminated union 按 type 正确分发到 TushareProviderSetting；未知 type 抛异常
- TestProvidersSetting    集合创建；get() 分发与 KeyError；export()/describe() 结构正确
- TestFromYaml            从真实 providers.yml 加载并校验字段
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from app.common.setting.bridges import (
    BridgesCacheSetting,
    BridgesSetting,
    ProviderSetting,
    TushareProviderSetting,
)

_VALID_PROVIDERS_DATA = {
    "providers": {
        "tushare": {
            "type": "tushare",
            "name": "tushare",
            "region": "cn",
            "secret": "testtoken1234567890abcdef",
            "ttl_seconds": 1800,
            "ttl_margin": 60,
            "use_cache": True,
            "jitter_min_seconds": 1.0,
            "jitter_max_seconds": 1.5,
        }
    }
}

_REQUIRED = {"secret": "testtoken1234567890abcdef"}

_ALL_EXPORT_KEYS = [
    "category",
    "type",
    "name",
    "region",
    "secret",
    "ttl_seconds",
    "ttl_margin",
    "use_cache",
    "jitter_min_seconds",
    "jitter_max_seconds",
]


def _make(**kwargs) -> TushareProviderSetting:
    return TushareProviderSetting(**{**_REQUIRED, **kwargs})


# ──────────────────────────────────────────────────────────────────────────────
# TestTushareDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestTushareDefaults:
    def test_type_default(self):
        assert _make().type == "tushare"

    def test_name_default(self):
        assert _make().name == "tushare"

    def test_region_default(self):
        assert _make().region == "cn"

    def test_ttl_seconds_default(self):
        assert _make().ttl_seconds == 1800

    def test_ttl_margin_default(self):
        assert _make().ttl_margin == 60

    def test_use_cache_default(self):
        assert _make().use_cache is True

    def test_jitter_min_seconds_default(self):
        assert _make().jitter_min_seconds == 0.2

    def test_jitter_max_seconds_default(self):
        assert _make().jitter_max_seconds == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# TestTushareValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestTushareValidation:
    def test_missing_secret_raises(self):
        with pytest.raises(ValidationError):
            TushareProviderSetting()

    def test_custom_secret_stored(self):
        assert _make().secret == "testtoken1234567890abcdef"

    def test_custom_region_stored(self):
        assert _make(region="us").region == "us"

    def test_custom_ttl_seconds_stored(self):
        assert _make(ttl_seconds=3600).ttl_seconds == 3600

    def test_custom_use_cache_stored(self):
        assert _make(use_cache=False).use_cache is False

    def test_custom_jitter_stored(self):
        obj = _make(jitter_min_seconds=0.5, jitter_max_seconds=2.0)
        assert obj.jitter_min_seconds == 0.5
        assert obj.jitter_max_seconds == 2.0


# ──────────────────────────────────────────────────────────────────────────────
# TestTushareExport
# ──────────────────────────────────────────────────────────────────────────────


class TestTushareExport:
    def test_export_returns_dict(self):
        assert isinstance(_make().export(), dict)

    def test_export_contains_all_keys(self):
        result = _make().export()
        for key in _ALL_EXPORT_KEYS:
            assert key in result, f"missing key: {key}"

    def test_export_secret_is_masked(self):
        result = _make().export()
        assert result["secret"].endswith("***")
        assert result["secret"].startswith("test")

    def test_export_values_match_fields(self):
        obj = _make(ttl_seconds=900, use_cache=False)
        result = obj.export()
        assert result["ttl_seconds"] == 900
        assert result["use_cache"] is False
        assert result["type"] == "tushare"
        assert result["category"] == "TushareProviderSetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestProviderUnion
# ──────────────────────────────────────────────────────────────────────────────


class TestProviderUnion:
    def test_tushare_type_resolves_to_tushare_setting(self):
        ta = TypeAdapter(ProviderSetting)
        result = ta.validate_python({"type": "tushare", **_REQUIRED})
        assert isinstance(result, TushareProviderSetting)

    def test_unknown_type_raises(self):
        ta = TypeAdapter(ProviderSetting)
        with pytest.raises((ValidationError, Exception)):
            ta.validate_python({"type": "unknown_provider", **_REQUIRED})


# ──────────────────────────────────────────────────────────────────────────────
# TestProvidersSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesSetting:
    def test_create_returns_bridges_setting(self):
        result = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(result, BridgesSetting)

    def test_create_with_tushare_key(self):
        result = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert "tushare" in result.providers

    def test_get_provider_returns_tushare_setting(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(ps.get_provider("tushare"), TushareProviderSetting)

    def test_get_provider_returns_correct_values(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        ts = ps.get_provider("tushare")
        assert ts.region == "cn"
        assert ts.ttl_seconds == 1800
        assert ts.use_cache is True

    def test_get_provider_missing_provider_raises_keyerror(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        with pytest.raises(KeyError):
            ps.get_provider("nonexistent")

    def test_export_returns_dict(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(ps.export(), dict)

    def test_export_contains_tushare_key(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert "tushare" in ps.export()["providers"]

    def test_export_each_entry_is_dict_or_list(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        for entry in ps.export().values():
            assert isinstance(entry, dict) or isinstance(entry, list)

    def test_describe_returns_valid_json(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        parsed = json.loads(ps.describe())
        assert isinstance(parsed, dict)
        assert "tushare" in parsed["providers"]


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_loads_real_bridges_yml(self):
        from pathlib import Path

        real_path = Path(__file__).parent.parent.parent.parent.parent / "setting" / "bridges.yml"
        if not real_path.is_file():
            pytest.skip("setting/bridges.yml not present")
        ps = BridgesSetting.from_yaml(real_path)
        assert isinstance(ps, BridgesSetting)

    def test_real_yml_tushare_accessible(self):
        from pathlib import Path

        real_path = Path(__file__).parent.parent.parent.parent.parent / "setting" / "bridges.yml"
        if not real_path.is_file():
            pytest.skip("setting/bridges.yml not present")
        ts = BridgesSetting.from_yaml(real_path).get_provider("tushare")
        assert isinstance(ts, TushareProviderSetting)
        assert ts.secret
        assert ts.ttl_seconds > 0


# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesCacheSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesCacheSetting:
    def test_defaults_name(self):
        assert BridgesCacheSetting().name == "cache"

    def test_defaults_path(self):
        assert BridgesCacheSetting().path == ".cache/bridges/cache.duckdb"

    def test_defaults_ttl_hours(self):
        assert BridgesCacheSetting().ttl_hours == 48

    def test_defaults_ttl_table(self):
        assert BridgesCacheSetting().ttl_table == "__system_ttl"

    def test_defaults_hash_length(self):
        assert BridgesCacheSetting().hash_length == 16

    def test_custom_path_stored(self):
        s = BridgesCacheSetting(path="/tmp/test.duckdb")
        assert s.path == "/tmp/test.duckdb"

    def test_custom_ttl_hours_stored(self):
        s = BridgesCacheSetting(ttl_hours=24)
        assert s.ttl_hours == 24

    def test_custom_hash_length_stored(self):
        s = BridgesCacheSetting(hash_length=8)
        assert s.hash_length == 8

    def test_export_returns_dict(self):
        assert isinstance(BridgesCacheSetting().export(), dict)

    def test_export_contains_all_keys(self):
        result = BridgesCacheSetting().export()
        for key in ("name", "path", "ttl_hours", "ttl_table", "hash_length", "category"):
            assert key in result, f"missing key: {key}"

    def test_export_values_match_defaults(self):
        result = BridgesCacheSetting().export()
        assert result["ttl_hours"] == 48
        assert result["hash_length"] == 16

    def test_bridges_setting_cache_defaults(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(ps.cache, BridgesCacheSetting)
        assert ps.cache.ttl_hours == 48

    def test_bridges_setting_custom_cache(self):
        data = {**_VALID_PROVIDERS_DATA, "cache": {"ttl_hours": 12, "hash_length": 8}}
        ps = BridgesSetting(**data)
        assert ps.cache.ttl_hours == 12
        assert ps.cache.hash_length == 8

    def test_bridges_setting_export_includes_cache(self):
        ps = BridgesSetting(**_VALID_PROVIDERS_DATA)
        assert "cache" in ps.export()
