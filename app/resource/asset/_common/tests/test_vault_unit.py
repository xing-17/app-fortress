from __future__ import annotations

from typing import ClassVar

import pytest

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._vault import BaseVault
from app.setting._vault import UnionVaultSetting


class _ConcreteVault(BaseVault):
    # BaseVault is abstract (uri/frn/from_setting/asset).
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"

    @classmethod
    def from_setting(cls, setting: UnionVaultSetting) -> "_ConcreteVault":
        return cls(name=setting.name)

    def asset(
        self,
        rel: str,
        filekind: AssetFileKind | None = None,
        partitions: list[str] | None = None,
    ) -> BaseAsset:
        raise NotImplementedError


class TestBaseVaultConstruction:
    def test_cannot_instantiate_without_overriding_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseVault()

    def test_no_authorized_flag_is_required(self):
        # Unlike BaseAsset/BaseAssetfile, BaseVault is not a GovernedAssetResource.
        vault = _ConcreteVault()
        assert isinstance(vault, _ConcreteVault)


class TestBaseVaultDefaults:
    def test_default_name_is_none(self):
        vault = _ConcreteVault()
        assert vault.name is None

    def test_default_description_is_empty_string(self):
        vault = _ConcreteVault()
        assert vault.description == ""


class TestBaseVaultTags:
    def test_tags_include_platform_and_filesystem(self):
        vault = _ConcreteVault()
        assert vault.tags == {"platform": Platform.LOCAL, "filesystem": AssetFilesystem.LOCAL}
