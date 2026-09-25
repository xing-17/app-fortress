from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
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
