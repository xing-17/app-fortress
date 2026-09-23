from __future__ import annotations

import pytest
from pydantic import ValidationError

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
        assert vault.prefix == ""


class TestOSSVaultDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert vault.prefix == "my/prefix"

    def test_none_prefix_becomes_empty_string(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert vault.prefix == ""


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
        assert vault.uri == "s3://my-bucket/my/prefix"


class TestOSSVaultFrn:
    def test_frn_returns_oss_vault_identifier(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert vault.frn == f"vault:{Platform.ALIYUN}:my-bucket/my/prefix"
