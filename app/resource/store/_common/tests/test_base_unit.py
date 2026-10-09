from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._base import BaseStoreResource, GovernedStoreResource


class _ConcreteStoreResource(BaseStoreResource):
    # BaseStoreResource declares no abstract members of its own, unlike BaseStore/BaseDatabase/BaseTable.
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL


class _ConcreteGovernedStoreResource(GovernedStoreResource):
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL


class TestBaseStoreResourceInit:
    def test_directly_instantiable_without_subclassing_abstract_members(self):
        resource = _ConcreteStoreResource(name="s")
        assert resource.name == "s"

    def test_default_identity_is_none(self):
        resource = _ConcreteStoreResource(name="s")
        assert resource.identity is None

    def test_default_tags_include_only_storesystem_platform_and_name(self):
        resource = _ConcreteStoreResource(name="s")
        assert resource.tags == {
            "storesystem": StoreSystem.FILE,
            "platform": Platform.LOCAL,
            "name": "s",
        }

    def test_explicit_tags_are_merged_with_non_override_tags(self):
        resource = _ConcreteStoreResource(name="s", tags={"env": "prod"})
        assert resource.tags == {
            "env": "prod",
            "storesystem": StoreSystem.FILE,
            "platform": Platform.LOCAL,
            "name": "s",
        }

    def test_tags_cannot_override_storesystem_platform_and_name(self):
        resource = _ConcreteStoreResource(
            name="s",
            tags={"storesystem": "fake", "platform": "fake", "name": "fake"},
        )
        assert resource.tags["storesystem"] == StoreSystem.FILE
        assert resource.tags["platform"] == Platform.LOCAL
        assert resource.tags["name"] == "s"


class TestBaseStoreResourceHandleIoError:
    def test_non_strict_swallows_exception(self):
        resource = _ConcreteStoreResource(name="s")
        resource._handle_io_error(ValueError("boom"), strict=False)

    def test_strict_reraises_same_exception(self):
        resource = _ConcreteStoreResource(name="s")
        _error = ValueError("boom")
        with pytest.raises(ValueError, match="boom"):
            resource._handle_io_error(_error, strict=True)


class TestBaseStoreResourceExport:
    def test_export_identity_is_none_when_identity_not_set(self):
        resource = _ConcreteStoreResource(name="s")
        result = resource.export()
        assert result["identity"] is None

    def test_export_identity_uses_name_attribute_when_present(self):
        identity = LocalIdentity(name="my_identity")
        resource = _ConcreteStoreResource(name="s", identity=identity)
        result = resource.export()
        assert result["identity"] == "my_identity"


class TestGovernedStoreResourceConstruction:
    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteGovernedStoreResource(name="s")

    def test_authorized_false_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteGovernedStoreResource(name="s", _authorized=False)

    def test_authorized_true_allows_construction(self):
        resource = _ConcreteGovernedStoreResource(name="s", _authorized=True)
        assert isinstance(resource, _ConcreteGovernedStoreResource)


class TestGovernedStoreResourceValidateName:
    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            _ConcreteGovernedStoreResource(name=bad_name, _authorized=True)

    def test_accepts_single_segment_name(self):
        resource = _ConcreteGovernedStoreResource(name="valid_name", _authorized=True)
        assert resource.name == "valid_name"
