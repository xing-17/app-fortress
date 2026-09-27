from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss._client import OSSClient
from app.resource.asset.oss.asset import OSSAsset
from app.resource.asset.oss.assetfile import OSSAssetfile
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOSSAssetInit:
    def test_missing_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAsset(region="cn-hangzhou")

    def test_missing_region_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSAsset(bucket="my-bucket")

    def test_default_identity_is_aliyun_identity_default(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.identity.name == AliyunIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.filesystem == AssetFilesystem.OSS
        assert asset.platform == Platform.ALIYUN

    def test_default_prefix_is_empty_string(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.prefix == ""

    def test_default_filekind_is_object(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.partitions == []


class TestOSSAssetDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert asset.prefix == "my/prefix"

    def test_none_prefix_becomes_empty_string(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert asset.prefix == ""


class TestOSSAssetDeriveIdentity:
    def test_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", identity="registered_aliyun_identity")
        assert asset.identity is _identity

    def test_platform_mismatch_raises_value_error(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSAsset(bucket="my-bucket", region="cn-hangzhou", identity="a_local_identity")


class TestOSSAssetUri:
    def test_uri_returns_oss_scheme_with_bucket_and_prefix(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert asset.uri == "oss://my-bucket/my/prefix"


class TestOSSAssetFrn:
    def test_frn_returns_oss_asset_identifier(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert asset.frn == f"asset:{Platform.ALIYUN}:my-bucket/my/prefix"


class TestOSSAssetTags:
    def test_tags_always_include_platform_filesystem_filekind(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", tags={"env": "prod"})
        assert asset.tags == {
            "env": "prod",
            "platform": Platform.ALIYUN,
            "filesystem": AssetFilesystem.OSS,
            "filekind": AssetFileKind.OBJECT,
        }


class TestOSSAssetExport:
    def test_export_includes_identity_name(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.export()["identity"] == AliyunIdentity.default().name


class TestOSSAssetFullPattern:
    def test_without_partitions_has_no_partition_segment(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert asset.full_pattern == "*my/prefix/*"

    def test_with_partitions_includes_partition_segment(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix", partitions=["year", "month"])
        assert asset.full_pattern == "*my/prefix/year=*/month=*/*"

    def test_with_filekind_restricts_object_segment(self):
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix", filekind=AssetFileKind.PARQUET)
        assert asset.full_pattern == "*my/prefix/*.parquet"


class TestOSSAssetClient:
    def test_client_property_resolves_via_oss_client_get_client(self, monkeypatch):
        _captured = {}

        def _fake_get_client(**kwargs):
            _captured.update(kwargs)
            return "fake-client"

        monkeypatch.setattr(OSSClient, "get_client", _fake_get_client)
        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", in_vpc=True)
        assert asset.client == "fake-client"
        assert _captured == {
            "bucket": "my-bucket",
            "region": "cn-hangzhou",
            "identity": asset.identity,
            "in_vpc": True,
        }


class TestOSSAssetListObjects:
    def test_builds_assetfile_for_each_target(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.list_objects.return_value = [
            {
                "bucket": "my-bucket",
                "key": "my/prefix/a.csv",
                "etag": "etag-a",
                "last_modified": 1_700_000_000.0,
                "size": 10,
                "storage_class": "Standard",
            },
        ]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        _files = asset.list_objects()

        assert len(_files) == 1
        _file = _files[0]
        assert isinstance(_file, OSSAssetfile)
        assert _file.key == "my/prefix/a.csv"
        assert _file.size == 10
        assert _file.modified_at == 1_700_000_000.0
        assert _file.metadata == {
            "etag": "etag-a",
            "last_modified": 1_700_000_000.0,
            "size": 10,
            "storage_class": "Standard",
        }

    def test_metadata_omits_none_values(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.list_objects.return_value = [
            {
                "bucket": "my-bucket",
                "key": "a.csv",
                "etag": None,
                "last_modified": None,
                "size": None,
                "storage_class": None,
            },
        ]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        _file = asset.list_objects()[0]
        assert _file.metadata == {}

    def test_forwards_pattern_since_until_recursive_to_client(self, monkeypatch):
        _captured = {}

        def _fake_list_objects(**kwargs):
            _captured.update(kwargs)
            return []

        _fake_client = MagicMock()
        _fake_client.list_objects.side_effect = _fake_list_objects
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        asset.list_objects(pattern="*.csv", since=1.0, until=2.0, recursive=False)
        assert _captured == {
            "prefix": "my/prefix",
            "pattern": "*.csv",
            "since": 1.0,
            "until": 2.0,
            "recursive": False,
        }

    def test_assetfile_inherits_asset_identity_tags_and_in_vpc(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.list_objects.return_value = [
            {
                "bucket": "my-bucket",
                "key": "a.csv",
                "etag": "e",
                "last_modified": 1.0,
                "size": 1,
                "storage_class": "Standard",
            },
        ]
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", tags={"env": "prod"}, in_vpc=True)
        _file = asset.list_objects()[0]
        assert _file.identity is asset.identity
        assert _file.tags["env"] == "prod"
        assert _file.in_vpc is True

    def test_no_targets_returns_empty_list(self, monkeypatch):
        _fake_client = MagicMock()
        _fake_client.list_objects.return_value = []
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou")
        assert asset.list_objects() == []


class TestOSSAssetListAssetfiles:
    def test_uses_full_pattern_and_forwards_recursive(self, monkeypatch):
        _captured = {}

        def _fake_list_objects(**kwargs):
            _captured.update(kwargs)
            return []

        _fake_client = MagicMock()
        _fake_client.list_objects.side_effect = _fake_list_objects
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)

        asset = OSSAsset(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        asset.list_assetfiles(recursive=False)
        assert _captured["pattern"] == asset.full_pattern
        assert _captured["recursive"] is False
