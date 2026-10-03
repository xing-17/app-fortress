from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.local.identity import LocalIdentity


class _ConcreteAsset(BaseAsset):
    # BaseAsset is abstract (uri/frn/name/full_pattern/list_assetfiles/list_objects); a trivial subclass lets us exercise its shared logic.
    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    @property
    def name(self) -> str:
        return "concrete"

    @property
    def full_pattern(self) -> str:
        return "concrete/*"

    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        limit: int | None = None,
    ) -> list[BaseAssetfile]:
        raise NotImplementedError

    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[BaseAssetfile]:
        raise NotImplementedError


class TestBaseAssetInit:
    def test_missing_required_fields_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteAsset()

    def test_default_filekind_is_object(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert asset.partitions == []

    def test_default_identity_is_none(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert asset.identity is None

    def test_partitions_default_factory_is_independent_per_instance(self):
        first = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.partitions.append("year=2026")
        assert second.partitions == []

    def test_tags_default_factory_is_independent_per_instance(self):
        first = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.tags["env"] = "prod"
        assert "env" not in second.tags

    def test_explicit_fields_are_kept(self):
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.OSS,
            platform=Platform.ALIYUN,
            filekind=AssetFileKind.PARQUET,
            partitions=["year=2026", "month=09"],
        )
        assert asset.filekind == AssetFileKind.PARQUET
        assert asset.partitions == ["year=2026", "month=09"]


class TestBaseAssetNonOverrideTags:
    def test_tags_always_include_platform_filesystem_and_filekind(self):
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"env": "prod"},
        )
        assert asset.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.OBJECT,
        }

    def test_tags_cannot_override_platform_filesystem_and_filekind(self):
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"platform": "fake", "filesystem": "fake", "filekind": "fake"},
        )
        assert asset.tags["platform"] == Platform.LOCAL
        assert asset.tags["filesystem"] == AssetFilesystem.LOCAL
        assert asset.tags["filekind"] == AssetFileKind.OBJECT


class TestBaseAssetExport:
    def test_export_includes_identity_name_when_identity_present(self):
        identity = LocalIdentity(name="my_identity")
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        result = asset.export()
        assert result["identity"] == "my_identity"

    def test_export_identity_is_none_when_identity_absent(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        result = asset.export()
        assert result["identity"] is None

    def test_describe_returns_valid_json_matching_export(self):
        identity = LocalIdentity(name="my_identity")
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        assert json.loads(asset.describe()) == asset.export()


class TestBaseAssetClone:
    def test_clone_without_updates_produces_equal_copy(self):
        identity = LocalIdentity(name="my_identity")
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        cloned = asset.clone()
        assert cloned is not asset
        assert cloned.export() == asset.export()

    def test_clone_with_updates_overrides_fields(self):
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            partitions=["year=2026"],
        )
        cloned = asset.clone(partitions=["year=2027"])
        assert cloned.partitions == ["year=2027"]
        assert asset.partitions == ["year=2026"]


class TestBaseAssetObjectPattern:
    def test_object_kind_returns_wildcard(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert asset.object_pattern == "*"

    def test_non_object_kind_returns_extension_pattern(self):
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            filekind=AssetFileKind.PARQUET,
        )
        assert asset.object_pattern == "*.parquet"


class TestBaseAssetPartitionPattern:
    def test_no_partitions_returns_wildcard(self):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert asset.partition_pattern == "*"

    def test_partitions_are_rendered_as_key_wildcard_pairs(self):
        # regression: partitions is list[str], IPartition.to_pattern must accept keys not a dict
        asset = _ConcreteAsset(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            partitions=["year", "month"],
        )
        assert asset.partition_pattern == "year=*/month=*"


class TestBaseAssetAssetfilesProperty:
    def test_first_access_calls_list_assetfiles(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=["file-a"]))
        assert asset.assetfiles == ["file-a"]
        asset.list_assetfiles.assert_called_once()

    def test_second_access_is_served_from_cache(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=["file-a"]))
        first = asset.assetfiles
        second = asset.assetfiles
        assert first is second
        asset.list_assetfiles.assert_called_once()

    def test_empty_result_is_still_cached(self, monkeypatch):
        # regression: `not self._assetfiles` would treat [] as "unset" and refetch every access
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=[]))
        assert asset.assetfiles == []
        assert asset.assetfiles == []
        asset.list_assetfiles.assert_called_once()


class TestBaseAssetLoadAssetfiles:
    def test_populates_cache_and_returns_result(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=["file-a"]))
        result = asset.load_assetfiles()
        assert result == ["file-a"]
        assert asset._assetfiles == ["file-a"]

    def test_without_force_does_not_refetch_when_cached(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=["file-a"]))
        asset.load_assetfiles()
        asset.load_assetfiles()
        asset.list_assetfiles.assert_called_once()

    def test_force_true_always_refetches(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(side_effect=[["file-a"], ["file-b"]]))
        first = asset.load_assetfiles()
        second = asset.load_assetfiles(force=True)
        assert first == ["file-a"]
        assert second == ["file-b"]
        assert asset._assetfiles == ["file-b"]
        assert asset.list_assetfiles.call_count == 2

    def test_forwards_since_and_until_to_list_assetfiles(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=[]))
        _since = datetime(2026, 1, 1)
        _until = datetime(2026, 2, 1)
        asset.load_assetfiles(since=_since, until=_until)
        asset.list_assetfiles.assert_called_once_with(since=_since, until=_until)


class TestBaseAssetResetAssetfiles:
    def test_clears_cached_assetfiles(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(return_value=["file-a"]))
        asset.load_assetfiles()
        asset.reset_assetfiles()
        assert asset._assetfiles is None

    def test_next_access_refetches_after_reset(self, monkeypatch):
        asset = _ConcreteAsset(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteAsset, "list_assetfiles", MagicMock(side_effect=[["file-a"], ["file-b"]]))
        asset.load_assetfiles()
        asset.reset_assetfiles()
        result = asset.load_assetfiles()
        assert result == ["file-b"]
        assert asset.list_assetfiles.call_count == 2
