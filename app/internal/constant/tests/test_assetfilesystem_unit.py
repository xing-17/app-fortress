from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.assetfilesystem import AssetFilesystem


class TestAssetFilesystemValues:
    def test_local_value(self):
        assert AssetFilesystem.LOCAL == "local"

    def test_oss_value(self):
        assert AssetFilesystem.OSS == "oss"

    def test_members_count(self):
        assert len(AssetFilesystem) == 2


class TestAssetFilesystemBehaviour:
    def test_is_str_enum(self):
        assert issubclass(AssetFilesystem, StrEnum)

    def test_lookup_by_value(self):
        assert AssetFilesystem("local") is AssetFilesystem.LOCAL

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AssetFilesystem("invalid")
