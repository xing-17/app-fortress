from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.local.local import LocalIdentity


class _ConcreteAssetfile(BaseAssetfile):
    # BaseAssetfile is abstract (uri/stem/extension/name/frn/read_bytes/write_bytes/load);
    # a trivial subclass lets us exercise its shared logic.
    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def stem(self) -> str:
        return "concrete"

    @property
    def extension(self) -> str:
        return "ext"

    @property
    def name(self) -> str:
        return "concrete.ext"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    def read_bytes(self) -> bytes:
        raise NotImplementedError

    def write_bytes(
        self,
        data: bytes,
    ) -> None:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError


class TestBaseAssetfileInit:
    def test_missing_required_fields_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteAssetfile()

    def test_default_filekind_is_object(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_dict(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.partitions == {}

    def test_default_size_is_none(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.size is None

    def test_default_modified_at_is_none(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.modified_at is None

    def test_default_identity_is_none(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.identity is None

    def test_default_metadata_is_empty_dict(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert assetfile.metadata == {}

    def test_partitions_default_factory_is_independent_per_instance(self):
        first = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.partitions["year"] = "2026"
        assert second.partitions == {}

    def test_metadata_default_factory_is_independent_per_instance(self):
        first = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.metadata["key"] = "value"
        assert second.metadata == {}

    def test_tags_default_factory_is_independent_per_instance(self):
        first = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.tags["env"] = "prod"
        assert "env" not in second.tags

    def test_explicit_fields_are_kept(self):
        assetfile = _ConcreteAssetfile(
            filesystem=AssetFilesystem.OSS,
            platform=Platform.ALIYUN,
            filekind=AssetFileKind.PARQUET,
            partitions={"year": "2026", "month": "09"},
            size=1024,
        )
        assert assetfile.filekind == AssetFileKind.PARQUET
        assert assetfile.partitions == {"year": "2026", "month": "09"}
        assert assetfile.size == 1024


class TestBaseAssetfileNonOverrideTags:
    def test_tags_always_include_platform_filesystem_and_filekind(self):
        assetfile = _ConcreteAssetfile(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"env": "prod"},
        )
        assert assetfile.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.OBJECT,
        }

    def test_tags_cannot_override_platform_filesystem_and_filekind(self):
        assetfile = _ConcreteAssetfile(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"platform": "fake", "filesystem": "fake", "filekind": "fake"},
        )
        assert assetfile.tags["platform"] == Platform.LOCAL
        assert assetfile.tags["filesystem"] == AssetFilesystem.LOCAL
        assert assetfile.tags["filekind"] == AssetFileKind.OBJECT


class TestBaseAssetfileExport:
    def test_export_includes_identity_name_when_identity_present(self):
        identity = LocalIdentity(name="my_identity")
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        result = assetfile.export()
        assert result["identity"] == "my_identity"

    def test_export_identity_is_none_when_identity_absent(self):
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        result = assetfile.export()
        assert result["identity"] is None

    def test_describe_returns_valid_json_matching_export(self):
        identity = LocalIdentity(name="my_identity")
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        assert json.loads(assetfile.describe()) == assetfile.export()


class TestBaseAssetfileClone:
    def test_clone_without_updates_produces_equal_copy(self):
        identity = LocalIdentity(name="my_identity")
        assetfile = _ConcreteAssetfile(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        cloned = assetfile.clone()
        assert cloned is not assetfile
        assert cloned.export() == assetfile.export()

    def test_clone_with_updates_overrides_fields(self):
        assetfile = _ConcreteAssetfile(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            partitions={"year": "2026"},
        )
        cloned = assetfile.clone(partitions={"year": "2027"})
        assert cloned.partitions == {"year": "2027"}
        assert assetfile.partitions == {"year": "2026"}
