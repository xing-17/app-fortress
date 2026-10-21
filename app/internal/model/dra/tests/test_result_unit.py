from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.model.dra import (
    DRAColumnDefinition,
    DRADataResult,
    DRADatasetResult,
    DRADefinitionResult,
    DRAQualityResult,
)


class TestDRADatasetResult:
    def test_defaults(self):
        result = DRADatasetResult(name="src.ds")
        assert result.description == ""
        assert result.partitions == []

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            DRADatasetResult()

    def test_is_frozen(self):
        result = DRADatasetResult(name="src.ds")
        with pytest.raises(ValidationError):
            result.name = "other"

    def test_default_lists_are_not_shared(self):
        a = DRADatasetResult(name="a")
        b = DRADatasetResult(name="b")
        assert a.partitions is not b.partitions


class TestDRAColumnDefinition:
    def test_nullable_defaults_to_true(self):
        column = DRAColumnDefinition(name="id", type="BIGINT")
        assert column.nullable is True

    @pytest.mark.parametrize("field", ["name", "type"])
    def test_required_fields(self, field):
        kwargs = {"name": "id", "type": "BIGINT"}
        del kwargs[field]
        with pytest.raises(ValidationError):
            DRAColumnDefinition(**kwargs)

    def test_is_frozen(self):
        column = DRAColumnDefinition(name="id", type="BIGINT")
        with pytest.raises(ValidationError):
            column.nullable = False


class TestDRADefinitionResult:
    def test_columns_are_required(self):
        with pytest.raises(ValidationError):
            DRADefinitionResult(dataset="src.ds")

    def test_columns_accept_dicts(self):
        result = DRADefinitionResult(
            dataset="src.ds",
            columns=[{"name": "id", "type": "BIGINT", "nullable": False}],
        )
        assert isinstance(result.columns[0], DRAColumnDefinition)
        assert result.columns[0].nullable is False
        assert result.partitions == []

    def test_invalid_column_is_rejected(self):
        with pytest.raises(ValidationError):
            DRADefinitionResult(dataset="src.ds", columns=[{"name": "id"}])


class TestDRAQualityResult:
    def test_records_default_to_empty(self):
        assert DRAQualityResult(dataset="src.ds").records == []

    def test_records_are_kept(self):
        records = [{"rule": "not_null", "passed": True}]
        assert DRAQualityResult(dataset="src.ds", records=records).records == records


class TestDRADataResult:
    def _kwargs(self, **overrides):
        kwargs = {"columns": ["a"], "types": ["BIGINT"], "rows": [[1], [2]]}
        kwargs.update(overrides)
        return kwargs

    def test_defaults(self):
        result = DRADataResult(**self._kwargs())
        assert result.truncated is False
        assert result.truncated_by is None
        assert result.elapsed_ms == 0.0

    @pytest.mark.parametrize("field", ["columns", "types", "rows"])
    def test_required_fields(self, field):
        kwargs = self._kwargs()
        del kwargs[field]
        with pytest.raises(ValidationError):
            DRADataResult(**kwargs)

    @pytest.mark.parametrize("value", ["rows", "size", None])
    def test_truncated_by_accepts_valid_values(self, value):
        assert DRADataResult(**self._kwargs(truncated_by=value)).truncated_by == value

    def test_truncated_by_rejects_unknown_value(self):
        with pytest.raises(ValidationError):
            DRADataResult(**self._kwargs(truncated_by="time"))

    def test_rows_may_hold_mixed_types(self):
        result = DRADataResult(**self._kwargs(rows=[[1, "x", None, 1.5]]))
        assert result.rows == [[1, "x", None, 1.5]]

    def test_is_frozen(self):
        result = DRADataResult(**self._kwargs())
        with pytest.raises(ValidationError):
            result.truncated = True
