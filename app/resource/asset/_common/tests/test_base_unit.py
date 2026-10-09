from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource.asset._common._base import BaseAssetResource, GovernedAssetResource
from app.resource.identity.local.identity import LocalIdentity


class _ConcreteAssetResource(BaseAssetResource):
    # BaseAssetResource is abstract (uri/frn); a trivial subclass exercises its shared logic.
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"


class _ConcreteGovernedAssetResource(GovernedAssetResource):
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.LOCAL
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def uri(self) -> str:
        return "concrete://uri"

    @property
    def frn(self) -> str:
        return "concrete:frn"


class TestBaseAssetResourceInit:
    def test_cannot_instantiate_without_overriding_abstract_properties(self):
        with pytest.raises(TypeError):
            BaseAssetResource()

    def test_default_identity_is_none(self):
        resource = _ConcreteAssetResource()
        assert resource.identity is None

    def test_default_tags_contain_only_platform_and_filesystem(self):
        resource = _ConcreteAssetResource()
        assert resource.tags == {"platform": Platform.LOCAL, "filesystem": AssetFilesystem.LOCAL}

    def test_explicit_tags_are_merged_with_non_override_tags(self):
        resource = _ConcreteAssetResource(tags={"env": "prod"})
        assert resource.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
        }


class TestBaseAssetResourceExport:
    def test_export_identity_is_none_when_identity_not_set(self):
        resource = _ConcreteAssetResource()
        result = resource.export()
        assert result["identity"] is None

    def test_export_identity_uses_name_attribute_when_present(self):
        identity = LocalIdentity(name="my_identity")
        resource = _ConcreteAssetResource(identity=identity)
        result = resource.export()
        assert result["identity"] == "my_identity"


class TestGovernedAssetResourceConstruction:
    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteGovernedAssetResource()

    def test_authorized_false_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteGovernedAssetResource(_authorized=False)

    def test_authorized_true_allows_construction(self):
        resource = _ConcreteGovernedAssetResource(_authorized=True)
        assert isinstance(resource, _ConcreteGovernedAssetResource)
