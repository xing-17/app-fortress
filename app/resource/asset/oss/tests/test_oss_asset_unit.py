from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss.asset import OSSAsset
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
