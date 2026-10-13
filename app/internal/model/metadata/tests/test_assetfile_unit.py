from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from app.internal.model.definition import DataframeDefinition
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.model.quality import DataframeQuality


@pytest.fixture
def frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "b": [1, 2, 2, None],
            "a": ["x", "y", "y", "z"],
        }
    )


class TestAssetfileMetadataValidation:
    def test_quality_is_required(self):
        with pytest.raises(ValidationError):
            AssetfileMetadata(definition=DataframeDefinition())

    def test_definition_is_required(self):
        with pytest.raises(ValidationError):
            AssetfileMetadata(quality=DataframeQuality())

    def test_accepts_explicit_components(self):
        quality = DataframeQuality()
        definition = DataframeDefinition()
        result = AssetfileMetadata(quality=quality, definition=definition)
        assert result.quality.width == 0
        assert result.definition.columns == []

    def test_accepts_dict_components(self):
        result = AssetfileMetadata(
            quality={"width": 0, "height": 0},
            definition={"columns": [{"name": "a", "type": "Int64"}]},
        )
        assert isinstance(result.quality, DataframeQuality)
        assert result.definition.columns[0].name == "a"


class TestAssetfileMetadataFromFrame:
    def test_builds_both_components(self, frame):
        result = AssetfileMetadata.from_frame(frame)
        assert isinstance(result.quality, DataframeQuality)
        assert isinstance(result.definition, DataframeDefinition)

    def test_quality_reflects_frame_shape(self, frame):
        result = AssetfileMetadata.from_frame(frame)
        assert result.quality.width == 2
        assert result.quality.height == 4
        assert result.quality.complete_rows == 3
        assert result.quality.duplicate_rows == 2

    def test_definition_and_quality_columns_are_consistent(self, frame):
        result = AssetfileMetadata.from_frame(frame)
        definition_cols = {c.name: c.type for c in result.definition.columns}
        quality_cols = {c.name: c.type for c in result.quality.columns}
        assert definition_cols == quality_cols
        assert set(definition_cols) == {"a", "b"}

    def test_columns_are_sorted_by_name(self, frame):
        result = AssetfileMetadata.from_frame(frame)
        assert [c.name for c in result.definition.columns] == ["a", "b"]
        assert [c.name for c in result.quality.columns] == ["a", "b"]

    def test_null_count_is_reported(self, frame):
        result = AssetfileMetadata.from_frame(frame)
        column_b = next(c for c in result.quality.columns if c.name == "b")
        assert column_b.null_count == 1
        assert column_b.complete_count == 3

    def test_empty_frame_with_schema(self):
        df = pl.DataFrame(schema={"a": pl.Int64, "b": pl.String})
        result = AssetfileMetadata.from_frame(df)
        assert result.quality.is_empty is True
        assert result.quality.height == 0
        assert result.quality.width == 2
        assert [c.name for c in result.definition.columns] == ["a", "b"]

    def test_frame_without_columns(self):
        result = AssetfileMetadata.from_frame(pl.DataFrame())
        assert result.quality.is_empty is True
        assert result.quality.width == 0
        assert result.definition.columns == []

    def test_same_schema_gives_same_fingerprint(self, frame):
        other = pl.DataFrame({"a": ["p"], "b": [9]})
        first = AssetfileMetadata.from_frame(frame)
        second = AssetfileMetadata.from_frame(other)
        assert first.definition.fingerprint == second.definition.fingerprint

    def test_different_schema_gives_different_fingerprint(self, frame):
        other = pl.DataFrame({"a": ["p"], "b": ["not-int"]})
        first = AssetfileMetadata.from_frame(frame)
        second = AssetfileMetadata.from_frame(other)
        assert first.definition.fingerprint != second.definition.fingerprint


class TestAssetfileMetadataSerialization:
    def test_export_round_trip(self, frame):
        original = AssetfileMetadata.from_frame(frame)
        restored = AssetfileMetadata.from_dict(original.export())
        assert restored.definition.fingerprint == original.definition.fingerprint
        assert restored.quality.height == original.quality.height
        assert [c.name for c in restored.quality.columns] == [c.name for c in original.quality.columns]

    def test_from_dict_returns_same_instance(self, frame):
        original = AssetfileMetadata.from_frame(frame)
        assert AssetfileMetadata.from_dict(original) is original
