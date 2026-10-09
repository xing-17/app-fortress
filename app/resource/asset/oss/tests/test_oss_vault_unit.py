from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.oss.asset import OSSAsset
from app.resource.asset.oss.vault import OSSVault
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity
from app.setting._vault import OSSVaultSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


@pytest.fixture(autouse=True)
def _fake_oss_client(monkeypatch):
    # OSSAsset/OSSVault never make real network calls; replace the lazy client with a mock.
    monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: MagicMock())


class TestOSSVaultInit:
    def test_missing_bucket_raises_validation_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OSSVault(region="cn-hangzhou")

    def test_missing_region_raises_validation_error(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OSSVault(bucket="my-bucket")

    def test_filesystem_and_platform_are_fixed(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.filesystem == AssetFilesystem.OSS
        assert vault.platform == Platform.ALIYUN

    def test_default_identity_is_aliyun_identity_default(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.identity.name == AliyunIdentity.default().name

    def test_default_prefix_is_vault(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.prefix == "vault"


class TestOSSVaultDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert vault.prefix == "my/prefix"

    def test_none_prefix_uses_default(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert vault.prefix == "vault"


class TestOSSVaultDeriveIdentity:
    def test_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", identity="registered_aliyun_identity")
        assert vault.identity is _identity

    def test_platform_mismatch_raises_value_error(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSVault(bucket="my-bucket", region="cn-hangzhou", identity="a_local_identity")


class TestOSSVaultFromSetting:
    def test_from_setting_copies_name_bucket_region_description_tags(self):
        setting = OSSVaultSetting(
            name="my_vault",
            bucket="my-bucket",
            region="cn-hangzhou",
            description="an oss vault",
            tags={"env": "test"},
        )
        vault = OSSVault.from_setting(setting)
        assert vault.name == "my_vault"
        assert vault.bucket == "my-bucket"
        assert vault.region == "cn-hangzhou"
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


class TestOSSVaultUriAndFrn:
    def test_uri_returns_oss_scheme_with_bucket_and_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.uri == "oss://my-bucket/vault"

    def test_frn_includes_platform_bucket_and_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        assert vault.frn == f"vault:platform={Platform.ALIYUN}:bucket=my-bucket:prefix=vault"


class TestOSSVaultAsset:
    def test_asset_key_is_relative_to_vault_prefix(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub/dir")
        assert isinstance(asset, OSSAsset)
        assert asset.prefix == "vault/sub/dir"

    def test_asset_strips_leading_and_trailing_slashes_from_rel(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("/sub/dir/")
        assert asset.prefix == "vault/sub/dir"

    def test_asset_inherits_vault_identity(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub")
        assert asset.identity is vault.identity

    def test_asset_inherits_vault_tags(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou", tags={"env": "prod"})
        asset = vault.asset("sub")
        assert asset.tags["env"] == "prod"

    def test_asset_inherits_vault_bucket_and_region(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub")
        assert asset.bucket == "my-bucket"
        assert asset.region == "cn-hangzhou"

    def test_asset_passes_through_filekind_and_partitions(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub", filekind=AssetFileKind.PARQUET, partitions=["year"])
        assert asset.filekind == AssetFileKind.PARQUET
        assert asset.partitions == ["year"]

    def test_asset_without_explicit_filekind_defaults_to_object(self):
        vault = OSSVault(bucket="my-bucket", region="cn-hangzhou")
        asset = vault.asset("sub")
        assert asset.filekind == AssetFileKind.OBJECT
        assert asset.partitions == []
