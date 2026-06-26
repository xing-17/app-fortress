"""
综合测试：app.common.setting.system

覆盖范围
--------
- TestDefaults    各字段默认值正确
- TestValidation  name 必填缺失时抛出 ValidationError；自定义值完整存储
- TestDescribe    describe() 返回包含全部字段且值与模型一致的字典
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.common.setting.system import SystemSetting

_ALL_KEYS = [
    "name",
    "version",
    "alias",
    "env",
    "timezone",
    "log_level",
    "log_format",
    "log_path",
    "log_file_max_mb",
    "log_group_max_len",
]


# ──────────────────────────────────────────────────────────────────────────────
# TestDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_version_default(self):
        assert SystemSetting(name="app").version == "1.0.0"

    def test_alias_default(self):
        assert SystemSetting(name="app").alias == "default"

    def test_env_default(self):
        assert SystemSetting(name="app").env == "prod"

    def test_timezone_default(self):
        assert SystemSetting(name="app").timezone == "UTC"

    def test_log_level_default(self):
        assert SystemSetting(name="app").log_level == "INFO"

    def test_log_format_default(self):
        assert SystemSetting(name="app").log_format == "TEXT"

    def test_log_path_default(self):
        assert SystemSetting(name="app").log_path == "./logs"

    def test_log_file_max_mb_default(self):
        assert SystemSetting(name="app").log_file_max_mb == 10

    def test_log_group_max_len_default(self):
        assert SystemSetting(name="app").log_group_max_len == 10000


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_name_required_raises_without_name(self):
        with pytest.raises(ValidationError):
            SystemSetting()

    def test_custom_values_stored_correctly(self):
        config = SystemSetting(
            name="fortress",
            version="6.0.0",
            alias="伽蓝",
            env="test",
            timezone="Asia/Shanghai",
            log_level="DEBUG",
            log_format="COLORTEXT",
            log_path="/tmp/logs",
            log_file_max_mb=50,
            log_group_max_len=5000,
        )
        assert config.name == "fortress"
        assert config.version == "6.0.0"
        assert config.alias == "伽蓝"
        assert config.env == "test"
        assert config.timezone == "Asia/Shanghai"
        assert config.log_level == "DEBUG"
        assert config.log_format == "COLORTEXT"
        assert config.log_path == "/tmp/logs"
        assert config.log_file_max_mb == 50
        assert config.log_group_max_len == 5000


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_str(self):
        assert isinstance(SystemSetting(name="app").describe(), str)

    def test_describe_contains_all_keys(self):
        result = SystemSetting(name="app").export()
        for key in _ALL_KEYS:
            assert key in result

    def test_describe_no_extra_keys(self):
        result = SystemSetting(name="app").export()
        assert set(result.keys()) == set(_ALL_KEYS)

    def test_describe_values_match_fields(self):
        config = SystemSetting(name="check", version="2.0.0", alias="tester")
        result = config.export()
        assert result["name"] == "check"
        assert result["version"] == "2.0.0"
        assert result["alias"] == "tester"
        assert result["env"] == config.env
        assert result["timezone"] == config.timezone
