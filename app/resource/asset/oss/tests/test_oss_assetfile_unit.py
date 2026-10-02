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
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOSSAssetfileInit:
    def test_missing_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(region="cn-hangzhou", key="report.csv")

    def test_missing_region_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", key="report.csv")

    def test_missing_key_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou")

    def test_default_identity_is_aliyun_identity_default(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assert assetfile.identity.name == AliyunIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assert assetfile.filesystem == AssetFilesystem.OSS
        assert assetfile.platform == Platform.ALIYUN

    def test_default_filekind_is_object(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.unknownext")
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_dict(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assert assetfile.partitions == {}


class TestOSSAssetfileDeriveKey:
    def test_leading_slashes_are_stripped(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="/my/prefix/report.csv")
        assert assetfile.key == "my/prefix/report.csv"

    def test_empty_key_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="")

    def test_key_ending_with_slash_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="my/prefix/")


class TestOSSAssetfileDeriveIdentity:
    def test_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        assetfile = OSSAssetfile(
            bucket="my-bucket", region="cn-hangzhou", key="report.csv", identity="registered_aliyun_identity"
        )
        assert assetfile.identity is _identity

    def test_platform_mismatch_raises_value_error(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv", identity="a_local_identity")


class TestOSSAssetfileDerivePartitions:
    def test_partitions_are_parsed_from_key_segments(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="dt=2024-01-01/report.csv")
        assert assetfile.partitions == {"dt": "2024-01-01"}


class TestOSSAssetfileDeriveFilekind:
    def test_known_extension_resolves_to_matching_filekind(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.parquet")
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_unknown_extension_falls_back_to_object(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.unknownext")
        assert assetfile.filekind == AssetFileKind.OBJECT


class TestOSSAssetfileProperties:
    def test_uri_returns_oss_scheme_with_bucket_and_key(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="my/prefix/report.csv")
        assert assetfile.uri == "oss://my-bucket/my/prefix/report.csv"

    def test_stem_extension_and_name(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="my/prefix/report.csv")
        assert assetfile.stem == "report"
        assert assetfile.extension == "csv"
        assert assetfile.name == "report.csv"

    def test_frn_returns_oss_assetfile_identifier(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="my/prefix/report.csv")
        assert assetfile.frn == f"assetfile:{Platform.ALIYUN}:my-bucket/my/prefix/report.csv"


class TestOSSAssetfileTags:
    def test_tags_reflect_derived_filekind(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.parquet", tags={"env": "prod"})
        assert assetfile.tags == {
            "env": "prod",
            "platform": Platform.ALIYUN,
            "filesystem": AssetFilesystem.OSS,
            "filekind": AssetFileKind.PARQUET,
        }


class TestOSSAssetfileExport:
    def test_export_includes_identity_name(self):
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assert assetfile.export()["identity"] == AliyunIdentity.default().name


class TestOSSAssetfileClient:
    def test_client_property_resolves_via_oss_client_get_client(self, monkeypatch):
        _captured = {}

        def _fake_get_client(**kwargs):
            _captured.update(kwargs)
            return "fake-client"

        monkeypatch.setattr(OSSClient, "get_client", _fake_get_client)
        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv", in_vpc=True)
        assert assetfile.client == "fake-client"
        assert _captured == {
            "bucket": "my-bucket",
            "region": "cn-hangzhou",
            "identity": assetfile.identity,
            "in_vpc": True,
        }


class TestOSSAssetfileReadWriteBytes:
    def test_read_bytes_delegates_to_client_with_key(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.read_bytes.return_value = b"payload"
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assert assetfile.read_bytes() == b"payload"
        _fake_client.read_bytes.assert_called_once_with("report.csv")

    def test_read_bytes_missing_key_raises_file_not_found_error(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.read_bytes.side_effect = FileNotFoundError("report.csv")
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        with pytest.raises(FileNotFoundError):
            assetfile.read_bytes()

    def test_write_bytes_delegates_to_client_with_key_and_data(self, monkeypatch):
        _fake_client = MagicMock()
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assetfile.write_bytes(b"a,b,c")
        _fake_client.write_bytes.assert_called_once_with(key="report.csv", data=b"a,b,c")


class TestOSSAssetfileLoad:
    def test_load_populates_size_and_modified_at(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.get_object.return_value = {
            "etag": "etag-a",
            "last_modified": 1_700_000_000.0,
            "size": 123,
            "storage_class": "Standard",
        }
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assetfile.load()
        assert assetfile.size == 123
        assert assetfile.modified_at == 1_700_000_000.0

    def test_load_merges_fetched_fields_into_metadata(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.get_object.return_value = {
            "etag": "etag-a",
            "last_modified": 1_700_000_000.0,
            "size": 123,
            "storage_class": "Standard",
        }
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(
            bucket="my-bucket", region="cn-hangzhou", key="report.csv", metadata={"custom": "value"}
        )
        assetfile.load()
        assert assetfile.metadata["custom"] == "value"
        assert assetfile.metadata["etag"] == "etag-a"

    def test_load_calls_get_object_with_key(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.get_object.return_value = {
            "etag": "e",
            "last_modified": 1.0,
            "size": 1,
            "storage_class": "Standard",
        }
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        assetfile.load()
        _fake_client.get_object.assert_called_once_with("report.csv")

    def test_load_missing_key_raises_file_not_found_error(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.get_object.side_effect = FileNotFoundError("report.csv")
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        assetfile = OSSAssetfile(bucket="my-bucket", region="cn-hangzhou", key="report.csv")
        with pytest.raises(FileNotFoundError):
            assetfile.load()
