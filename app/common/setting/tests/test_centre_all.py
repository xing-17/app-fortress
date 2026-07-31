"""
综合测试：app.common.setting.centre

覆盖范围
--------
- TestDefaults    各字段默认值正确
- TestValidation  target 必填；缺失时抛 ValidationError；自定义值正确存储
- TestCategory    category 固定为 "CentreSetting"
- TestFromYaml    从合法 YAML 文件加载；路径不存在抛 FileNotFoundError
- TestExport      export() 包含全部字段（含 category）
- TestDescribe    describe() 返回合法 JSON；值与 export() 一致
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.common.setting.centre import CentreSetting

_VALID_DATA = {
    "connection": "prod",
    "path": ".cache/centre/centre.duckdb",
    "max_threads": 1,
    "max_queue_size": 100,
    "extensions": ["httpfs"],
    "settings": {
        "memory_limit": "12GB",
        "max_temp_directory_size": "20GB",
        "enable_object_cache": True,
        "preserve_insertion_order": False,
    },
}

_ALL_KEYS = [
    "category",
    "connection",
    "path",
    "max_threads",
    "extensions",
    "settings",
]


# ──────────────────────────────────────────────────────────────────────────────
# TestDefaults
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_path_default(self):
        assert CentreSetting(connection="dev").path == ".cache/centre/centre.duckdb"

    def test_threads_default(self):
        assert CentreSetting(connection="dev").max_threads == 1

    def test_extensions_default(self):
        assert CentreSetting(connection="dev").extensions == ["httpfs", "s3"]

    def test_settings_default_is_empty_dict(self):
        assert CentreSetting(connection="dev").settings == {}


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_target_required_raises_without_it(self):
        with pytest.raises(ValidationError):
            CentreSetting()

    def test_custom_target_stored(self):
        assert CentreSetting(connection="staging").connection == "staging"

    def test_custom_path_stored(self):
        obj = CentreSetting(connection="dev", path="/data/my.duckdb")
        assert obj.path == "/data/my.duckdb"

    def test_custom_threads_stored(self):
        assert CentreSetting(connection="dev", max_threads=4).max_threads == 4

    def test_custom_extensions_stored(self):
        obj = CentreSetting(connection="dev", extensions=["httpfs", "parquet"])
        assert obj.extensions == ["httpfs", "parquet"]

    def test_custom_settings_stored(self):
        obj = CentreSetting(connection="dev", settings={"memory_limit": "8GB"})
        assert obj.settings["memory_limit"] == "8GB"


# ──────────────────────────────────────────────────────────────────────────────
# TestCategory
# ──────────────────────────────────────────────────────────────────────────────


class TestCategory:
    def test_category_equals_classname(self):
        assert CentreSetting(connection="dev").category == "CentreSetting"

    def test_category_in_export(self):
        assert CentreSetting(connection="dev").export()["category"] == "CentreSetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_missing_file_raises_filenotfounderror(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            CentreSetting.from_yaml(tmp_path / "nonexistent.yml")

    def test_valid_yaml_returns_centresetting(self, tmp_path: Path):
        p = tmp_path / "centre.yml"
        p.write_text(yaml.dump(_VALID_DATA), encoding="utf-8")
        obj = CentreSetting.from_yaml(p)
        assert isinstance(obj, CentreSetting)

    def test_valid_yaml_populates_target(self, tmp_path: Path):
        p = tmp_path / "centre.yml"
        p.write_text(yaml.dump(_VALID_DATA), encoding="utf-8")
        assert CentreSetting.from_yaml(p).connection == "prod"

    def test_valid_yaml_populates_settings(self, tmp_path: Path):
        p = tmp_path / "centre.yml"
        p.write_text(yaml.dump(_VALID_DATA), encoding="utf-8")
        obj = CentreSetting.from_yaml(p)
        assert obj.settings["memory_limit"] == "12GB"

    def test_loads_real_centre_yml(self):
        real_path = Path(__file__).parent.parent.parent.parent.parent / "setting" / "centre.yml"
        if not real_path.is_file():
            pytest.skip("setting/centre.yml not present")
        obj = CentreSetting.from_yaml(real_path)
        assert isinstance(obj, CentreSetting)
        assert obj.connection


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        assert isinstance(CentreSetting(connection="dev").export(), dict)

    def test_export_contains_all_keys(self):
        data = CentreSetting(connection="dev").export()
        for key in _ALL_KEYS:
            assert key in data, f"missing key: {key}"

    def test_export_values_match_fields(self):
        obj = CentreSetting(connection="prod", max_threads=4)
        data = obj.export()
        assert data["connection"] == "prod"
        assert data["max_threads"] == 4


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_valid_json(self):
        raw = CentreSetting(connection="dev").describe()
        assert isinstance(json.loads(raw), dict)

    def test_describe_matches_export(self):
        obj = CentreSetting(connection="prod", max_threads=2)
        assert json.loads(obj.describe()) == obj.export()
