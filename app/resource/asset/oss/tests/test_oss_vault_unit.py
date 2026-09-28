from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss.vault import OSSVault
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity
from app.setting._vault import OSSVaultSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOSSVaultInit:
    def test_missing_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSVault(region="cn-hangzhou")

    def test_missing_region_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSVault(bucket="my-bucket")

    def test_default_identity_is_aliyun_identity_default(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.identity.name == AliyunIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.filesystem == AssetFilesystem.OSS
        assert vault.platform == Platform.ALIYUN

    def test_default_prefix_is_empty_string(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.prefix == "vault"


class TestOSSVaultDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert vault.prefix == "my/prefix"

    def test_none_prefix_becomes_empty_string(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert vault.prefix == "vault"


class TestOSSVaultFromSetting:
    def test_from_setting_copies_bucket_region_prefix(self):
        setting = OSSVaultSetting(
            name="my_vault",
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="my/prefix",
            description="an oss vault",
            tags={"env": "test"},
        )
        vault = OSSVault.from_setting(setting)
        assert vault.name == "my_vault"
        assert vault.bucket == "my-bucket"
        assert vault.region == "cn-hangzhou"
        assert vault.prefix == "my/prefix"
        assert vault.description == "an oss vault"
        assert vault.tags["env"] == "test"

    def test_from_setting_uses_default_identity_when_not_specified(self):
        setting = OSSVaultSetting(name="my_vault", bucket="my-bucket", region="cn-hangzhou")
        vault = OSSVault.from_setting(setting)
        assert vault.identity.name == AliyunIdentity.default().name

    def test_from_setting_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        setting = OSSVaultSetting(
            name="my_vault",
            bucket="my-bucket",
            region="cn-hangzhou",
            identity="registered_aliyun_identity",
        )
        vault = OSSVault.from_setting(setting)
        assert vault.identity is _identity

    def test_from_setting_raises_value_error_on_platform_mismatch(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        setting = OSSVaultSetting(
            name="my_vault",
            bucket="my-bucket",
            region="cn-hangzhou",
            identity="a_local_identity",
        )
        with pytest.raises(ValueError):
            OSSVault.from_setting(setting)


class TestOSSVaultUri:
    def test_uri_returns_s3_scheme_with_bucket_and_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert vault.uri == "oss://my-bucket/my/prefix"


class TestOSSVaultFrn:
    def test_frn_returns_oss_vault_identifier(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert vault.frn == f"vault:{Platform.ALIYUN}:my-bucket/my/prefix"


class TestOSSVaultAsset:
    def test_asset_prefix_joins_vault_prefix_and_rel(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        asset = vault.asset("sub/dir")
        assert asset.prefix == "my/prefix/sub/dir"

    def test_asset_prefix_without_vault_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub/dir")
        assert asset.prefix == "vault/sub/dir"

    def test_leading_slash_in_rel_does_not_override_vault_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        asset = vault.asset("/etc/passwd")
        assert asset.prefix == "my/prefix/etc/passwd"

    def test_asset_inherits_vault_bucket_and_region(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub")
        assert asset.bucket == "my-bucket"
        assert asset.region == "cn-hangzhou"

    def test_asset_inherits_vault_identity(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub")
        assert asset.identity is vault.identity

    def test_asset_inherits_vault_tags(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", tags={"env": "prod"})
        asset = vault.asset("sub")
        assert asset.tags["env"] == "prod"

    def test_asset_passes_through_filekind_and_partitions(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub", filekind=AssetFileKind.PARQUET, partitions=["year=2024"])
        assert asset.filekind == AssetFileKind.PARQUET
        assert asset.partitions == ["year=2024"]
