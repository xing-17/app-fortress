from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.model.definition import ColumnDesc as ExportedColumnDesc
from app.internal.model.definition.desc import ColumnDesc


class TestColumnDescConstruction:
    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            ColumnDesc()

    def test_description_and_unit_default_to_empty(self):
        result = ColumnDesc(name="a")
        assert result.name == "a"
        assert result.description == ""
        assert result.unit == ""

    def test_all_fields_are_kept(self):
        result = ColumnDesc(name="a", description="Weight", unit="kg")
        assert (result.name, result.description, result.unit) == ("a", "Weight", "kg")

    def test_none_falls_back_to_default(self):
        result = ColumnDesc(name="a", description=None, unit=None)
        assert result.description == ""
        assert result.unit == ""

    def test_none_name_is_rejected(self):
        with pytest.raises(ValidationError):
            ColumnDesc(name=None)

    def test_non_string_value_is_rejected(self):
        with pytest.raises(ValidationError):
            ColumnDesc(name="a", unit=["kg"])

    def test_extra_fields_are_ignored(self):
        result = ColumnDesc(name="a", unknown=1)
        assert not hasattr(result, "unknown")

    def test_is_exported_from_package(self):
        assert ExportedColumnDesc is ColumnDesc


class TestColumnDescFrozen:
    @pytest.mark.parametrize("field", ["name", "description", "unit"])
    def test_assignment_is_rejected(self, field):
        result = ColumnDesc(name="a")
        with pytest.raises(ValidationError):
            setattr(result, field, "x")
        assert result.name == "a"

    def test_is_hashable(self):
        first = ColumnDesc(name="a", description="d", unit="u")
        second = ColumnDesc(name="a", description="d", unit="u")
        assert len({first, second}) == 1

    def test_equal_by_value(self):
        assert ColumnDesc(name="a", unit="kg") == ColumnDesc(name="a", unit="kg")
        assert ColumnDesc(name="a", unit="kg") != ColumnDesc(name="a", unit="g")


class TestColumnDescBehavior:
    def test_from_dict_builds_instance(self):
        result = ColumnDesc.from_dict({"name": "a", "unit": "kg"})
        assert result == ColumnDesc(name="a", unit="kg")

    def test_from_dict_returns_same_instance(self):
        original = ColumnDesc(name="a")
        assert ColumnDesc.from_dict(original) is original

    def test_export_returns_plain_dict(self):
        result = ColumnDesc(name="a", description="Weight", unit="kg").export()
        assert result == {"name": "a", "description": "Weight", "unit": "kg"}

    def test_export_round_trips(self):
        original = ColumnDesc(name="a", description="Weight", unit="kg")
        assert ColumnDesc.from_dict(original.export()) == original

    def test_clone_applies_updates_without_touching_original(self):
        original = ColumnDesc(name="a", unit="kg")
        result = original.clone(unit="g")
        assert result.unit == "g"
        assert original.unit == "kg"

    def test_non_ascii_text_is_kept(self):
        result = ColumnDesc(name="a", description="成交额", unit="万元")
        assert result.export()["description"] == "成交额"
        assert "万元" in result.describe()

    def test_sha256_follows_content(self):
        first = ColumnDesc(name="a", unit="kg")
        assert first.sha256() == ColumnDesc(name="a", unit="kg").sha256()
        assert first.sha256() != ColumnDesc(name="a", unit="g").sha256()
