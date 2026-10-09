from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.local.identity import LocalIdentity


class _ConcreteAssetfile(BaseAssetfile):
    # BaseAssetfile is abstract (stem/extension/name/uri/frn/read_bytes/write_bytes/load).
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
        return b"data"

    def write_bytes(self, data: bytes) -> None:
        return None

    def load(self) -> None:
        return None


class TestBaseAssetfileConstruction:
    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteAssetfile()

    def test_authorized_true_allows_construction(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert isinstance(assetfile, _ConcreteAssetfile)

    def test_cannot_instantiate_without_overriding_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseAssetfile(_authorized=True)


class TestBaseAssetfileDefaults:
    def test_default_filekind_is_object(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_dict(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.partitions == {}

    def test_default_size_and_modified_at_are_none(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.size is None
        assert assetfile.modified_at is None

    def test_default_metadata_is_empty_dict(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.metadata == {}


class TestBaseAssetfileTags:
    def test_tags_include_platform_filesystem_and_filekind(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.tags == {
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.OBJECT,
        }


class TestBaseAssetfileReadWriteLoad:
    def test_read_bytes_returns_expected_bytes(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assert assetfile.read_bytes() == b"data"

    def test_write_bytes_does_not_raise(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assetfile.write_bytes(b"new data")

    def test_load_does_not_raise(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        assetfile.load()


class TestBaseAssetfileExport:
    def test_export_identity_is_none_when_identity_not_set(self):
        assetfile = _ConcreteAssetfile(_authorized=True)
        result = assetfile.export()
        assert result["identity"] is None

    def test_export_identity_uses_name_attribute_when_present(self):
        identity = LocalIdentity(name="my_identity")
        assetfile = _ConcreteAssetfile(_authorized=True, identity=identity)
        result = assetfile.export()
        assert result["identity"] == "my_identity"
