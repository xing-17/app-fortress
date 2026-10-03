from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._base import BaseStoreResource, GovernedStoreResource


class TestBaseStoreResourceInstantiation:
    def test_directly_instantiable_without_subclassing(self):
        # BaseStoreResource has no @abstractmethod of its own, unlike BaseStore/BaseDatabase/BaseTable.
        resource = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert resource.name == "s"

    def test_default_identity_is_none(self):
        resource = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert resource.identity is None

    def test_default_tags_is_empty_factory(self):
        first = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        second = BaseStoreResource(name="t", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        first.tags["env"] = "prod"
        assert "env" not in second.tags


class TestBaseStoreResourceNonOverrideTags:
    def test_tags_always_include_storesystem_platform_and_name(self):
        resource = BaseStoreResource(
            name="s",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            tags={"env": "prod"},
        )
        assert resource.tags == {
            "env": "prod",
            "storesystem": StoreSystem.FILE,
            "platform": Platform.LOCAL,
            "name": "s",
        }

    def test_tags_cannot_override_storesystem_platform_and_name(self):
        resource = BaseStoreResource(
            name="s",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            tags={"storesystem": "fake", "platform": "fake", "name": "fake"},
        )
        assert resource.tags["storesystem"] == StoreSystem.FILE
        assert resource.tags["platform"] == Platform.LOCAL
        assert resource.tags["name"] == "s"


class TestBaseStoreResourceHandleIoError:
    def test_non_strict_swallows_exception(self):
        resource = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        resource._handle_io_error(ValueError("boom"), strict=False)

    def test_strict_reraises_same_exception(self):
        resource = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        _error = ValueError("boom")
        with pytest.raises(ValueError, match="boom"):
            resource._handle_io_error(_error, strict=True)


class TestBaseStoreResourceExport:
    def test_export_includes_identity_name_when_identity_present(self):
        identity = LocalIdentity(name="my_identity")
        resource = BaseStoreResource(
            name="s",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            identity=identity,
        )
        assert resource.export()["identity"] == "my_identity"

    def test_export_identity_is_none_when_identity_absent(self):
        resource = BaseStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert resource.export()["identity"] is None


class TestGovernedStoreResourceGuardConstruction:
    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            GovernedStoreResource(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)

    def test_authorized_false_raises_validation_error(self):
        with pytest.raises(ValidationError):
            GovernedStoreResource(
                name="s",
                storesystem=StoreSystem.FILE,
                platform=Platform.LOCAL,
                _authorized=False,
            )

    def test_authorized_true_succeeds(self):
        resource = GovernedStoreResource(
            name="s",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            _authorized=True,
        )
        assert resource.name == "s"


class TestGovernedStoreResourceValidateName:
    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            GovernedStoreResource(
                name=bad_name,
                storesystem=StoreSystem.FILE,
                platform=Platform.LOCAL,
                _authorized=True,
            )

    def test_accepts_single_segment_name(self):
        resource = GovernedStoreResource(
            name="valid_name",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            _authorized=True,
        )
        assert resource.name == "valid_name"
