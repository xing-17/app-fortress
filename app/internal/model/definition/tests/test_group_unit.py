from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.model.definition.dataframe import ColumnDefinition
from app.internal.model.definition.group import DefinitionGroup


class TestDefinitionGroupConstruction:
    def test_fingerprint_is_required(self):
        with pytest.raises(ValidationError):
            DefinitionGroup()

    def test_defaults_are_empty_lists(self):
        result = DefinitionGroup(fingerprint="abc")
        assert result.fingerprint == "abc"
        assert result.columns == []
        assert result.partitions == []

    def test_default_lists_are_not_shared(self):
        first = DefinitionGroup(fingerprint="a")
        second = DefinitionGroup(fingerprint="b")
        first.columns.append(ColumnDefinition(name="x", type="Int64"))
        first.partitions.append({"dt": "2024-01-01"})
        assert second.columns == []
        assert second.partitions == []

    def test_none_lists_fall_back_to_defaults(self):
        result = DefinitionGroup(fingerprint="abc", columns=None, partitions=None)
        assert result.columns == []
        assert result.partitions == []

    def test_columns_accept_dicts(self):
        result = DefinitionGroup(
            fingerprint="abc",
            columns=[{"name": "id", "type": "Int64"}],
        )
        assert result.columns == [ColumnDefinition(name="id", type="Int64")]

    def test_partitions_are_kept(self):
        partitions = [{"dt": "2024-01-01"}, {"dt": "2024-01-02"}]
        result = DefinitionGroup(fingerprint="abc", partitions=partitions)
        assert result.partitions == partitions

    def test_invalid_column_is_rejected(self):
        with pytest.raises(ValidationError):
            DefinitionGroup(fingerprint="abc", columns=[{"name": "id"}])

    def test_non_string_partition_value_is_rejected(self):
        with pytest.raises(ValidationError):
            DefinitionGroup(fingerprint="abc", partitions=[{"dt": {"a": 1}}])

    def test_extra_fields_are_ignored(self):
        result = DefinitionGroup(fingerprint="abc", unknown=1)
        assert not hasattr(result, "unknown")


class TestDefinitionGroupBehavior:
    def test_assignment_is_validated(self):
        result = DefinitionGroup(fingerprint="abc")
        with pytest.raises(ValidationError):
            result.partitions = "not-a-list"

    def test_from_dict_roundtrip(self):
        source = DefinitionGroup(
            fingerprint="abc",
            columns=[ColumnDefinition(name="id", type="Int64")],
            partitions=[{"dt": "2024-01-01"}],
        )
        assert DefinitionGroup.from_dict(source.export()) == source

    def test_from_dict_returns_same_instance(self):
        source = DefinitionGroup(fingerprint="abc")
        assert DefinitionGroup.from_dict(source) is source

    def test_export_is_json_serializable(self):
        result = DefinitionGroup(
            fingerprint="abc",
            columns=[ColumnDefinition(name="id", type="Int64")],
            partitions=[{"dt": "2024-01-01"}],
        )
        assert result.export() == {
            "fingerprint": "abc",
            "columns": [{"name": "id", "type": "Int64"}],
            "partitions": [{"dt": "2024-01-01"}],
        }

    def test_clone_is_deep_and_applies_updates(self):
        source = DefinitionGroup(fingerprint="abc", partitions=[{"dt": "1"}])
        copy = source.clone(fingerprint="xyz")
        copy.partitions[0]["dt"] = "2"
        assert copy.fingerprint == "xyz"
        assert source.fingerprint == "abc"
        assert source.partitions == [{"dt": "1"}]

    def test_sha256_is_stable_and_content_sensitive(self):
        first = DefinitionGroup(fingerprint="abc")
        same = DefinitionGroup(fingerprint="abc")
        other = DefinitionGroup(fingerprint="abd")
        assert first.sha256() == same.sha256()
        assert first.sha256() != other.sha256()
