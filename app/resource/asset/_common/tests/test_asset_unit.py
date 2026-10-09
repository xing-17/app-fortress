from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import pytest

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.local.identity import LocalIdentity


class _ConcreteAssetfile(BaseAssetfile):
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def stem(self) -> str:
        return "stem"

    @property
    def extension(self) -> str:
        return "ext"

    @property
    def name(self) -> str:
        return "stem.ext"

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    def read_bytes(self) -> bytes:
        return b""

    def write_bytes(self, data: bytes) -> None:
        return None

    def load(self) -> None:
        return None


class _ConcreteAsset(BaseAsset):
    # BaseAsset is abstract (name/full_pattern/assetfile/list_assetfiles/list_objects).
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def name(self) -> str:
        return "concrete_asset"

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    @property
    def full_pattern(self) -> str:
        return f"{self.partition_pattern}/{self.object_pattern}"

    def assetfile(
        self,
        name: str,
        partitions: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> BaseAssetfile:
        return _ConcreteAssetfile(_authorized=True, partitions=partitions or {})

    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[BaseAssetfile]:
        return []

    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[BaseAssetfile]:
        return []


class TestBaseAssetConstruction:
    def test_missing_authorized_flag_raises_validation_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _ConcreteAsset()

    def test_authorized_true_allows_construction(self):
        asset = _ConcreteAsset(_authorized=True)
        assert isinstance(asset, _ConcreteAsset)

    def test_cannot_instantiate_without_overriding_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseAsset(_authorized=True)


class TestBaseAssetDefaults:
    def test_default_filekind_is_object(self):
        asset = _ConcreteAsset(_authorized=True)
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self):
        asset = _ConcreteAsset(_authorized=True)
        assert asset.partitions == []


class TestBaseAssetObjectPattern:
    def test_object_filekind_returns_wildcard(self):
        asset = _ConcreteAsset(_authorized=True, filekind=AssetFileKind.OBJECT)
        assert asset.object_pattern == "*"

    def test_parquet_filekind_returns_extension_pattern(self):
        asset = _ConcreteAsset(_authorized=True, filekind=AssetFileKind.PARQUET)
        assert asset.object_pattern == "*.parquet"


class TestBaseAssetPartitionPattern:
    def test_no_partitions_returns_wildcard(self):
        asset = _ConcreteAsset(_authorized=True)
        assert asset.partition_pattern == "*"

    def test_partitions_return_key_equals_wildcard_segments(self):
        asset = _ConcreteAsset(_authorized=True, partitions=["year", "month"])
        assert asset.partition_pattern == "year=*/month=*"


class TestBaseAssetTags:
    def test_tags_include_platform_filesystem_and_filekind(self):
        asset = _ConcreteAsset(_authorized=True)
        assert asset.tags == {
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.OBJECT,
        }


class TestBaseAssetExport:
    def test_export_identity_is_none_when_identity_not_set(self):
        asset = _ConcreteAsset(_authorized=True)
        result = asset.export()
        assert result["identity"] is None

    def test_export_identity_uses_name_attribute_when_present(self):
        identity = LocalIdentity(name="my_identity")
        asset = _ConcreteAsset(_authorized=True, identity=identity)
        result = asset.export()
        assert result["identity"] == "my_identity"
