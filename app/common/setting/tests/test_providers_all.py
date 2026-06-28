"""
综合测试：app.common.setting.providers

覆盖范围
--------
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

from app.common.setting.providers import (
    ProviderSetting,
    ProvidersSetting,
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
            "retry_max": 2,
            "retry_wait": 60,
            "retry_rate": 1.0,
            "retry_skip_messages": ["不存在"],
            "coolant_interval": 0,
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
    "retry_max",
    "retry_wait",
    "retry_rate",
    "retry_skip_messages",
    "coolant_interval",
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

    def test_retry_max_default(self):
        assert _make().retry_max == 2

    def test_retry_wait_default(self):
        assert _make().retry_wait == 60

    def test_retry_rate_default(self):
        assert _make().retry_rate == 1.0

    def test_retry_skip_messages_default_is_empty(self):
        assert _make().retry_skip_messages == []

    def test_coolant_interval_default(self):
        assert _make().coolant_interval == 0

    def test_jitter_min_seconds_default(self):
        assert _make().jitter_min_seconds == 1.0

    def test_jitter_max_seconds_default(self):
        assert _make().jitter_max_seconds == 1.5


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

    def test_custom_retry_skip_messages_stored(self):
        obj = _make(retry_skip_messages=["不存在", "超限"])
        assert obj.retry_skip_messages == ["不存在", "超限"]

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

    def test_export_secret_not_masked(self):
        result = _make().export()
        assert result["secret"] == "testtoken1234567890abcdef"

    def test_export_values_match_fields(self):
        obj = _make(ttl_seconds=900, retry_max=3)
        result = obj.export()
        assert result["ttl_seconds"] == 900
        assert result["retry_max"] == 3
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


class TestProvidersSetting:
    def test_create_returns_providers_setting(self):
        result = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(result, ProvidersSetting)

    def test_create_with_tushare_key(self):
        result = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert "tushare" in result.providers

    def test_get_returns_tushare_setting(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(ps.get("tushare"), TushareProviderSetting)

    def test_get_returns_correct_values(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        ts = ps.get("tushare")
        assert ts.region == "cn"
        assert ts.ttl_seconds == 1800
        assert ts.retry_skip_messages == ["不存在"]

    def test_get_missing_provider_raises_keyerror(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        with pytest.raises(KeyError):
            ps.get("nonexistent")

    def test_export_returns_dict(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert isinstance(ps.export(), dict)

    def test_export_contains_providers_key(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert "providers" in ps.export()

    def test_export_providers_contains_tushare(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        assert "tushare" in ps.export()["providers"]

    def test_export_each_entry_is_dict(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        for entry in ps.export()["providers"].values():
            assert isinstance(entry, dict)

    def test_describe_returns_valid_json(self):
        ps = ProvidersSetting(**_VALID_PROVIDERS_DATA)
        parsed = json.loads(ps.describe())
        assert isinstance(parsed.get("providers"), dict)
        assert "tushare" in parsed["providers"]


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_loads_real_providers_yml(self):
        from pathlib import Path

        real_path = Path(__file__).parent.parent.parent.parent.parent / "setting" / "providers.yml"
        if not real_path.is_file():
            pytest.skip("setting/providers.yml not present")
        ps = ProvidersSetting.from_yaml(real_path)
        assert isinstance(ps, ProvidersSetting)

    def test_real_yml_tushare_accessible(self):
        from pathlib import Path

        real_path = Path(__file__).parent.parent.parent.parent.parent / "setting" / "providers.yml"
        if not real_path.is_file():
            pytest.skip("setting/providers.yml not present")
        ts = ProvidersSetting.from_yaml(real_path).get("tushare")
        assert isinstance(ts, TushareProviderSetting)
        assert ts.secret
        assert ts.ttl_seconds > 0
