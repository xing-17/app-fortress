from __future__ import annotations

import json

import pytest

from app.internal.abstract.setting import IAbstractSetting, IAbstractTaggedSetting


class _SampleSetting(IAbstractSetting):
    value: str = "fallback"
    nullable: str | None = "default_nullable"


class _SampleTaggedSetting(IAbstractTaggedSetting):
    name: str = "sample"

    def _non_override_tags(self) -> dict[str, str]:
        return {"name": self.name}


class TestIAbstractSettingPrepare:
    def test_explicit_none_for_field_with_default_falls_back_to_default(self):
        result = _SampleSetting.model_validate({"value": None})
        assert result.value == "fallback"

    def test_explicit_none_for_nullable_field_is_kept(self):
        result = _SampleSetting.model_validate({"nullable": None})
        assert result.nullable is None


class TestIAbstractSettingFromDict:
    def test_from_dict_builds_instance(self):
        result = _SampleSetting.from_dict({"value": "a"})
        assert isinstance(result, _SampleSetting)
        assert result.value == "a"


class TestIAbstractSettingFromYaml:
    def test_from_yaml_loads_valid_file(self, tmp_path):
        yaml_file = tmp_path / "setting.yaml"
        yaml_file.write_text("value: a\n", encoding="utf-8")
        result = _SampleSetting.from_yaml(yaml_file)
        assert result.value == "a"

    def test_from_yaml_missing_file_raises_file_not_found_error(self, tmp_path):
        missing = tmp_path / "missing.yaml"
        with pytest.raises(FileNotFoundError):
            _SampleSetting.from_yaml(missing)

    def test_from_yaml_invalid_yaml_raises_value_error(self, tmp_path):
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("value: [unclosed\n", encoding="utf-8")
        with pytest.raises(ValueError):
            _SampleSetting.from_yaml(yaml_file)


class TestIAbstractSettingClsName:
    def test_cls_name_returns_lowercased_class_name(self):
        instance = _SampleSetting(value="a")
        assert instance.cls_name == "_samplesetting"


class TestIAbstractSettingExportDescribe:
    def test_export_returns_json_serializable_dict(self):
        instance = _SampleSetting(value="a")
        assert instance.export() == {"value": "a", "nullable": "default_nullable"}

    def test_describe_returns_sorted_json_string(self):
        instance = _SampleSetting(value="a")
        assert json.loads(instance.describe()) == instance.export()


class TestIAbstractTaggedSetting:
    def test_tags_default_via_non_override_hook(self):
        instance = _SampleTaggedSetting()
        assert instance.tags == {"name": "sample"}

    def test_non_override_tags_overwrite_user_supplied_tags(self):
        instance = _SampleTaggedSetting(name="sample", tags={"name": "hijacked", "extra": "kept"})
        assert instance.tags == {"name": "sample", "extra": "kept"}
