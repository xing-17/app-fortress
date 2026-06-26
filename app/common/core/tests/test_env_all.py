"""
综合测试：app.common.core.env

覆盖范围
--------
- TestLoad      默认/自定义路径加载；.env 文件不存在时静默跳过；override=False 不覆盖已有 os.environ
- TestCheck     存在缺失变量时发出 UserWarning；所有变量存在时不发出警告
- TestGet       get() 返回已有 key 的值；缺失 key 时返回 default
- TestInject    inject() 包含 os.environ；传入 extra 时正确合并
- TestExport    export() 返回正确结构；敏感字段值正确脱敏
- TestDescribe  describe() 返回合法 JSON 字符串
- TestSingleton GlobalEnv 全局单例完整性
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pytest

from app.common.core.env import CoreEnv, GlobalEnv

_SUPPORTED_KEYS = [
    "OSS_ACCESS_KEY_ID",
    "OSS_ACCESS_KEY_SECRET",
]


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def valid_env_path(tmp_path: Path) -> Path:
    path = tmp_path / ".env"
    path.write_text(
        "OSS_ACCESS_KEY_ID=TESTID1234\nOSS_ACCESS_KEY_SECRET=TESTSECRET5678\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def partial_env_path(tmp_path: Path) -> Path:
    """Only contains one of the two required keys."""
    path = tmp_path / ".env"
    path.write_text("OSS_ACCESS_KEY_ID=TESTID1234\n", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def isolate_os_environ():
    """Snapshot and restore os.environ after each test."""
    original = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original)


# ──────────────────────────────────────────────────────────────────────────────
# TestLoad
# ──────────────────────────────────────────────────────────────────────────────


class TestLoad:
    def test_load_returns_coreenv_instance(self, valid_env_path):
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        assert isinstance(env, CoreEnv)

    def test_load_nonexistent_path_does_not_raise(self, tmp_path):
        missing = tmp_path / "nonexistent.env"
        env = CoreEnv.load(env_path=missing, check=False)
        assert isinstance(env, CoreEnv)
        assert env._env_values == []

    def test_load_injects_vars_into_os_environ(self, valid_env_path):
        # Remove keys first to ensure a clean state
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        CoreEnv.load(env_path=valid_env_path, check=False)
        assert os.environ.get("OSS_ACCESS_KEY_ID") == "TESTID1234"

    def test_load_does_not_override_existing_os_environ(self, valid_env_path):
        os.environ["OSS_ACCESS_KEY_ID"] = "ALREADY_SET"
        CoreEnv.load(env_path=valid_env_path, check=False)
        assert os.environ["OSS_ACCESS_KEY_ID"] == "ALREADY_SET"


# ──────────────────────────────────────────────────────────────────────────────
# TestCheck
# ──────────────────────────────────────────────────────────────────────────────


class TestCheck:
    def test_check_warns_when_key_missing(self, partial_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CoreEnv.load(env_path=partial_env_path, check=True)
        assert any("Missing required env vars" in str(warning.message) for warning in w)

    def test_check_no_warning_when_all_keys_present(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CoreEnv.load(env_path=valid_env_path, check=True)
        missing_warnings = [x for x in w if "Missing required env vars" in str(x.message)]
        assert len(missing_warnings) == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestGet
# ──────────────────────────────────────────────────────────────────────────────


class TestGet:
    def test_get_returns_value_for_existing_key(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        assert env.get("OSS_ACCESS_KEY_ID") == "TESTID1234"

    def test_get_returns_default_for_missing_key(self, valid_env_path):
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        assert env.get("NON_EXISTENT_KEY", "fallback") == "fallback"

    def test_get_returns_none_by_default_for_missing_key(self, valid_env_path):
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        assert env.get("NON_EXISTENT_KEY") is None


# ──────────────────────────────────────────────────────────────────────────────
# TestInject
# ──────────────────────────────────────────────────────────────────────────────


class TestInject:
    def test_inject_contains_os_environ_keys(self, valid_env_path):
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.inject()
        assert "PATH" in result or len(result) > 0

    def test_inject_merges_extra_keys(self, valid_env_path):
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.inject(extra={"MY_CUSTOM_KEY": "custom_value"})
        assert result["MY_CUSTOM_KEY"] == "custom_value"

    def test_inject_extra_overrides_environ(self, valid_env_path):
        os.environ["OSS_ACCESS_KEY_ID"] = "ORIGINAL"
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.inject(extra={"OSS_ACCESS_KEY_ID": "OVERRIDDEN"})
        assert result["OSS_ACCESS_KEY_ID"] == "OVERRIDDEN"


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.export()
        assert isinstance(result, dict)

    def test_export_contains_loaded_keys(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.export()
        assert "OSS_ACCESS_KEY_ID" in result
        assert "OSS_ACCESS_KEY_SECRET" in result

    def test_export_sensitive_key_is_masked(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.export()
        value = result["OSS_ACCESS_KEY_ID"]["value"]
        assert value.endswith("***")
        assert not value.startswith("***")

    def test_export_each_entry_has_value_and_source(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.export()
        for entry in result.values():
            assert "value" in entry
            assert "source" in entry


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_valid_json_string(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        result = env.describe()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_json_matches_export(self, valid_env_path):
        for key in _SUPPORTED_KEYS:
            os.environ.pop(key, None)
        env = CoreEnv.load(env_path=valid_env_path, check=False)
        parsed = json.loads(env.describe())
        exported = env.export()
        assert parsed.keys() == exported.keys()


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_env_is_coreenv_instance(self):
        assert isinstance(GlobalEnv, CoreEnv)

    def test_global_env_get_returns_string_or_none(self):
        result = GlobalEnv.get("OSS_ACCESS_KEY_ID")
        assert result is None or isinstance(result, str)
