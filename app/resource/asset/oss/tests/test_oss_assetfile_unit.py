from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss.assetfile import OSSAssetfile
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOSSAssetfileInit:
    def test_missing_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(region="cn-hangzhou", key="a.csv", _authorized=True)

    def test_missing_region_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", key="a.csv", _authorized=True)

    def test_missing_key_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", _authorized=True)

    def test_missing_authorized_raises_value_error(self):
        with pytest.raises(ValueError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="a.csv")

    def test_empty_key_raises_value_error(self):
        with pytest.raises(ValueError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="", _authorized=True)

    def test_key_ending_with_slash_raises_value_error(self):
        with pytest.raises(ValueError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="dir/", _authorized=True)

    def test_filesystem_and_platform_are_fixed(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="a.csv", _authorized=True)
        assert assetfile.filesystem == AssetFilesystem.OSS
        assert assetfile.platform == Platform.ALIYUN

    def test_default_identity_is_aliyun_identity_default(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="a.csv", _authorized=True)
        assert assetfile.identity.name == AliyunIdentity.default().name

    def test_default_size_and_modified_at_are_none(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="a.csv", _authorized=True)
        assert assetfile.size is None
        assert assetfile.modified_at is None


class TestOSSAssetfileDeriveKey:
    def test_leading_and_trailing_slashes_are_stripped(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="/dir/a.csv", _authorized=True)
        assert assetfile.key == "dir/a.csv"


class TestOSSAssetfileDeriveIdentity:
    def test_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        assetfile = OSSAssetfile(
            bucket="my-bucket",
            region="cn-hangzhou",
            key="a.csv",
            identity="registered_aliyun_identity",
            _authorized=True,
        )
        assert assetfile.identity is _identity

    def test_platform_mismatch_raises_value_error(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSAssetfile(
                bucket="my-bucket",
                region="cn-hangzhou",
                key="a.csv",
                identity="a_local_identity",
                _authorized=True,
            )


class TestOSSAssetfilePartitions:
    def test_explicit_partitions_are_kept_as_is(self):
        assetfile = OSSAssetfile(
            bucket="my-bucket",
            region="cn-hangzhou",
            key="a.csv",
            partitions={"year": "2024"},
            _authorized=True,
        )
        assert assetfile.partitions == {"year": "2024"}

    def test_partitions_are_not_derived_from_key(self):
        assetfile = OSSAssetfile(
            bucket="my-bucket",
            region="cn-hangzhou",
            key="year=2024/month=01/data.csv",
            _authorized=True,
        )
        assert assetfile.partitions == {}

    def test_no_partition_segments_results_in_empty_dict(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        assert assetfile.partitions == {}


class TestOSSAssetfileDeriveFilekind:
    def test_known_extension_maps_to_filekind(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.parquet", _authorized=True)
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_unknown_extension_defaults_to_object(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.unknownext", _authorized=True)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_no_extension_defaults_to_object(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data", _authorized=True)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_explicit_filekind_is_overridden_by_key_derived_value(self):
        # filekind is always re-derived from the key suffix, explicit value is not preserved
        assetfile = OSSAssetfile(
            bucket="my-bucket",
            region="cn-hangzhou",
            key="data.parquet",
            filekind=AssetFileKind.OBJECT,
            _authorized=True,
        )
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_tags_resync_with_derived_filekind(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.parquet", _authorized=True)
        assert assetfile.tags["filekind"] == AssetFileKind.PARQUET


class TestOSSAssetfileUriFrnStemExtensionName:
    def test_uri_returns_oss_scheme_with_bucket_and_key(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="dir/data.csv", _authorized=True)
        assert assetfile.uri == "oss://my-bucket/dir/data.csv"

    def test_frn_includes_platform_bucket_and_key(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="dir/data.csv", _authorized=True)
        assert assetfile.frn == f"assetfile:platform={Platform.ALIYUN}:bucket=my-bucket:key=dir/data.csv"

    def test_stem_and_extension_and_name(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="dir/data.csv", _authorized=True)
        assert assetfile.stem == "data"
        assert assetfile.extension == "csv"
        assert assetfile.name == "data.csv"


class TestOSSAssetfileWriteAndReadBytes:
    def test_write_bytes_delegates_to_client(self, monkeypatch):
        _client = MagicMock()
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        assetfile.write_bytes(b"hello")
        _client.write_bytes.assert_called_once_with(key="data.csv", data=b"hello")

    def test_read_bytes_delegates_to_client(self, monkeypatch):
        _client = MagicMock()
        _client.read_bytes.return_value = b"col1,col2\n1,2\n"
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        assert assetfile.read_bytes() == b"col1,col2\n1,2\n"
        _client.read_bytes.assert_called_once_with("data.csv")

    def test_read_bytes_missing_key_raises_file_not_found_error(self, monkeypatch):
        _client = MagicMock()
        _client.read_bytes.side_effect = FileNotFoundError("data.csv")
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        with pytest.raises(FileNotFoundError):
            assetfile.read_bytes()


class TestOSSAssetfileLoad:
    def test_load_refreshes_size_and_modified_at_from_metadata(self, monkeypatch):
        _client = MagicMock()
        _client.get_object.return_value = {"size": 5, "last_modified": 123.0, "etag": "e1"}
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        assert assetfile.size is None
        assetfile.load()
        assert assetfile.size == 5
        assert assetfile.modified_at == 123.0

    def test_load_updates_metadata_without_discarding_existing_keys(self, monkeypatch):
        _client = MagicMock()
        _client.get_object.return_value = {"size": 5, "last_modified": 123.0, "etag": "e1"}
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(
            bucket="my-bucket",
            region="cn-hangzhou",
            key="data.csv",
            metadata={"custom": "value"},
            _authorized=True,
        )
        assetfile.load()
        assert assetfile.metadata["custom"] == "value"
        assert assetfile.metadata["etag"] == "e1"

    def test_load_with_empty_metadata_does_not_update_size_or_modified_at(self, monkeypatch):
        _client = MagicMock()
        _client.get_object.return_value = {}
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="data.csv", _authorized=True)
        assetfile.load()
        assert assetfile.size is None
        assert assetfile.modified_at is None
