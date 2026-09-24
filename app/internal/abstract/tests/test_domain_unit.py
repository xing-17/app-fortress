from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.abstract.domain import IAbstractDomain, IAbstractTaggedDomain


class _SampleDomain(IAbstractDomain):
    value: str = "fallback"
    nullable: str | None = "default_nullable"


class _SampleTaggedDomain(IAbstractTaggedDomain):
    name: str = "sample"

    def _non_override_tags(self) -> dict[str, str]:
        return {"name": self.name}


class TestIAbstractDomainPrepare:
    def test_explicit_none_for_field_with_default_falls_back_to_default(self):
        result = _SampleDomain.model_validate({"value": None})
        assert result.value == "fallback"

    def test_explicit_none_for_nullable_field_is_kept(self):
        result = _SampleDomain.model_validate({"nullable": None})
        assert result.nullable is None

    def test_missing_key_uses_default(self):
        result = _SampleDomain.model_validate({})
        assert result.value == "fallback"
        assert result.nullable == "default_nullable"


class TestIAbstractDomainFromDict:
    def test_from_dict_with_plain_dict_builds_instance(self):
        result = _SampleDomain.from_dict({"value": "a"})
        assert isinstance(result, _SampleDomain)
        assert result.value == "a"

    def test_from_dict_with_existing_instance_returns_same_object(self):
        instance = _SampleDomain(value="a")
        result = _SampleDomain.from_dict(instance)
        assert result is instance


class TestIAbstractDomainModelConfig:
    def test_extra_fields_are_ignored(self):
        result = _SampleDomain.model_validate({"value": "a", "unknown_field": "x"})
        assert not hasattr(result, "unknown_field")

    def test_assignment_is_validated(self):
        instance = _SampleDomain(value="a")
        with pytest.raises(ValidationError):
            instance.value = 123  # type: ignore[assignment]


class TestIAbstractDomainClsName:
    def test_cls_name_returns_lowercased_class_name(self):
        instance = _SampleDomain(value="a")
        assert instance.cls_name == "_sampledomain"


class TestIAbstractDomainSha256:
    def test_sha256_is_stable_for_same_content(self):
        first = _SampleDomain(value="a")
        second = _SampleDomain(value="a")
        assert first.sha256() == second.sha256()

    def test_sha256_differs_for_different_content(self):
        first = _SampleDomain(value="a")
        second = _SampleDomain(value="b")
        assert first.sha256() != second.sha256()


class TestIAbstractDomainClone:
    def test_clone_without_updates_produces_equal_but_distinct_instance(self):
        instance = _SampleDomain(value="a")
        cloned = instance.clone()
        assert cloned is not instance
        assert cloned == instance

    def test_clone_with_updates_overrides_fields(self):
        instance = _SampleDomain(value="a")
        cloned = instance.clone(value="b")
        assert cloned.value == "b"
        assert instance.value == "a"


class TestIAbstractDomainExportDescribe:
    def test_export_returns_json_serializable_dict(self):
        instance = _SampleDomain(value="a")
        exported = instance.export()
        assert exported == {"value": "a", "nullable": "default_nullable"}

    def test_describe_returns_sorted_json_string(self):
        instance = _SampleDomain(value="a")
        described = instance.describe()
        assert json.loads(described) == instance.export()


class TestIAbstractTaggedDomain:
    def test_tags_default_to_empty_dict(self):
        instance = _SampleTaggedDomain()
        assert instance.tags == {"name": "sample"}

    def test_non_override_tags_overwrite_user_supplied_tags(self):
        instance = _SampleTaggedDomain(name="sample", tags={"name": "hijacked", "extra": "kept"})
        assert instance.tags == {"name": "sample", "extra": "kept"}
