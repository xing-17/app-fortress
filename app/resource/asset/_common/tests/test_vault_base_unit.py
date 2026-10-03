from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._vault import BaseVault
from app.resource.identity.local.identity import LocalIdentity
from app.setting._vault import LocalVaultSetting


class _ConcreteVault(BaseVault):
    # BaseVault is abstract (uri/frn/asset/from_setting); a trivial subclass lets us exercise its shared logic.
    @classmethod
    def from_setting(
        cls,
        setting: LocalVaultSetting,
    ) -> "_ConcreteVault":
        raise NotImplementedError

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> BaseAsset:
        raise NotImplementedError


class TestBaseVaultInit:
    def test_missing_required_fields_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteVault()

    def test_default_name_and_identity_are_none(self):
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert vault.name is None
        assert vault.identity is None

    def test_default_description_is_empty_string(self):
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        assert vault.description == ""

    def test_tags_default_factory_is_independent_per_instance(self):
        first = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        second = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL)
        first.tags["env"] = "prod"
        assert "env" not in second.tags

    def test_explicit_fields_are_kept(self):
        vault = _ConcreteVault(
            filesystem=AssetFilesystem.OSS,
            platform=Platform.ALIYUN,
            name="my_vault",
            description="a vault",
        )
        assert vault.name == "my_vault"
        assert vault.description == "a vault"


class TestBaseVaultNonOverrideTags:
    def test_tags_always_include_platform_and_filesystem(self):
        vault = _ConcreteVault(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"env": "prod"},
        )
        assert vault.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
        }

    def test_tags_cannot_override_platform_and_filesystem(self):
        vault = _ConcreteVault(
            filesystem=AssetFilesystem.LOCAL,
            platform=Platform.LOCAL,
            tags={"platform": "fake", "filesystem": "fake"},
        )
        assert vault.tags["platform"] == Platform.LOCAL
        assert vault.tags["filesystem"] == AssetFilesystem.LOCAL


class TestBaseVaultExport:
    def test_export_includes_identity_name_when_identity_present(self):
        identity = LocalIdentity(name="my_identity")
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        result = vault.export()
        assert result["identity"] == "my_identity"

    def test_describe_returns_valid_json_matching_export(self):
        identity = LocalIdentity(name="my_identity")
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        assert json.loads(vault.describe()) == vault.export()


class TestBaseVaultClone:
    def test_clone_without_updates_produces_equal_copy(self):
        identity = LocalIdentity(name="my_identity")
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, identity=identity)
        cloned = vault.clone()
        assert cloned is not vault
        assert cloned.export() == vault.export()

    def test_clone_with_updates_overrides_fields(self):
        vault = _ConcreteVault(filesystem=AssetFilesystem.LOCAL, platform=Platform.LOCAL, name="my_vault")
        cloned = vault.clone(name="cloned_vault")
        assert cloned.name == "cloned_vault"
        assert vault.name == "my_vault"


class TestBaseVaultFromSetting:
    def test_from_setting_is_a_placeholder_returning_none(self):
        # BaseVault.from_setting is meant to be overridden by subclasses;
        # on the base class itself it is a no-op stub.
        setting = LocalVaultSetting(name="my_vault", path="/tmp/my_vault")
        assert BaseVault.from_setting(setting) is None
