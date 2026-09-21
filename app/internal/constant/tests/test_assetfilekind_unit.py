from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.assetfilekind import AssetFileKind


class TestAssetFileKindValues:
    def test_parquet_value(self):
        assert AssetFileKind.PARQUET == "parquet"

    def test_object_value(self):
        assert AssetFileKind.OBJECT == "object"

    def test_members_count(self):
        assert len(AssetFileKind) == 2


class TestAssetFileKindBehaviour:
    def test_is_str_enum(self):
        assert issubclass(AssetFileKind, StrEnum)

    def test_lookup_by_value(self):
        assert AssetFileKind("parquet") is AssetFileKind.PARQUET

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AssetFileKind("invalid")
