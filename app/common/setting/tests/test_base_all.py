"""
综合测试：app.common.setting.base

覆盖范围
--------
- TestCategory    category 返回类名；子类返回子类名
- TestFromYaml    路径不存在抛 FileNotFoundError；空 YAML 触发 UserWarning；合法 YAML 正确实例化
- TestExport      export() 包含所有字段（含 category computed_field）
- TestDescribe    describe() 返回合法 JSON；值与 export() 一致
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.common.setting.base import BaseSetting

# ── 测试用具体子类 ────────────────────────────────────────────────────────────


class _Simple(BaseSetting):
    name: str
    value: int = 0


class _Child(_Simple):
    extra: str = "child"


# ──────────────────────────────────────────────────────────────────────────────
# TestCategory
# ──────────────────────────────────────────────────────────────────────────────


class TestCategory:
    def test_base_subclass_category_equals_classname(self):
        obj = _Simple(name="x")
        assert obj.category == "_Simple"

    def test_child_category_equals_child_classname(self):
        obj = _Child(name="x")
        assert obj.category == "_Child"

    def test_category_included_in_export(self):
        obj = _Simple(name="x")
        assert "category" in obj.export()

    def test_category_value_matches_classname(self):
        obj = _Simple(name="abc")
        assert obj.export()["category"] == "_Simple"


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_missing_file_raises_filenotfounderror(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            _Simple.from_yaml(tmp_path / "nonexistent.yml")

    def test_empty_yaml_emits_userwarning(self, tmp_path: Path):
        p = tmp_path / "empty.yml"
        p.write_text("", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                _Simple.from_yaml(p)
            except Exception:
                pass
            assert any(issubclass(x.category, UserWarning) for x in w)

    def test_invalid_yaml_raises_valueerror(self, tmp_path: Path):
        p = tmp_path / "bad.yml"
        p.write_text("name: [unclosed", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            _Simple.from_yaml(p)

    def test_valid_yaml_returns_instance(self, tmp_path: Path):
        p = tmp_path / "simple.yml"
        p.write_text(yaml.dump({"name": "hello", "value": 42}), encoding="utf-8")
        obj = _Simple.from_yaml(p)
        assert isinstance(obj, _Simple)

    def test_valid_yaml_populates_fields(self, tmp_path: Path):
        p = tmp_path / "simple.yml"
        p.write_text(yaml.dump({"name": "hello", "value": 42}), encoding="utf-8")
        obj = _Simple.from_yaml(p)
        assert obj.name == "hello"
        assert obj.value == 42

    def test_missing_required_field_raises_validationerror(self, tmp_path: Path):
        p = tmp_path / "simple.yml"
        p.write_text(yaml.dump({"value": 1}), encoding="utf-8")
        with pytest.raises(ValidationError):
            _Simple.from_yaml(p)

    def test_path_as_string_accepted(self, tmp_path: Path):
        p = tmp_path / "simple.yml"
        p.write_text(yaml.dump({"name": "str-path"}), encoding="utf-8")
        obj = _Simple.from_yaml(str(p))
        assert obj.name == "str-path"


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        assert isinstance(_Simple(name="x").export(), dict)

    def test_export_contains_all_fields(self):
        data = _Simple(name="x", value=7).export()
        assert data["name"] == "x"
        assert data["value"] == 7
        assert data["category"] == "_Simple"


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_valid_json(self):
        raw = _Simple(name="x").describe()
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_describe_matches_export(self):
        obj = _Simple(name="x", value=3)
        assert json.loads(obj.describe()) == obj.export()
