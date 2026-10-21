from __future__ import annotations

import json
from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity._common._secret import BaseSecret
from app.setting._identity import LocalIdentitySetting


class _ConcreteSecret(BaseSecret):
    platform: ClassVar[Platform] = Platform.LOCAL


class _ConcreteIdentity(BaseIdentity):
    platform: ClassVar[Platform] = Platform.LOCAL

    # BaseIdentity is abstract (frn); a trivial subclass lets us exercise its shared logic.
    @property
    def frn(self) -> str:
        return "concrete:frn"

    @classmethod
    def from_setting(cls, setting: LocalIdentitySetting) -> _ConcreteIdentity:
        return cls(name=setting.name)

    @classmethod
    def default(cls) -> _ConcreteIdentity:
        return cls(name="default_identity")

    def as_secret(self) -> _ConcreteSecret:
        return _ConcreteSecret()


class TestBaseIdentityInit:
    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteIdentity()

    def test_default_platform_is_local(self):
        identity = _ConcreteIdentity(name="my_identity")
        assert identity.platform == Platform.LOCAL

    def test_default_tags_contain_only_platform(self):
        identity = _ConcreteIdentity(name="my_identity")
        assert identity.tags == {"platform": Platform.LOCAL}

    def test_tags_default_factory_is_independent_per_instance(self):
        first = _ConcreteIdentity(name="first")
        second = _ConcreteIdentity(name="second")
        first.tags["env"] = "prod"
        assert second.tags == {"platform": Platform.LOCAL}


class TestBaseIdentityExport:
    def test_export_returns_expected_dict(self):
        identity = _ConcreteIdentity(name="my_identity", tags={"env": "prod"})
        result = identity.export()
        assert result == {
            "name": "my_identity",
            "tags": {"env": "prod", "platform": Platform.LOCAL.value},
        }

    def test_describe_returns_valid_json_matching_export(self):
        identity = _ConcreteIdentity(name="my_identity")
        assert json.loads(identity.describe()) == identity.export()


class TestBaseIdentityClone:
    def test_clone_without_updates_produces_equal_copy(self):
        identity = _ConcreteIdentity(name="my_identity", tags={"env": "prod"})
        cloned = identity.clone()
        assert cloned is not identity
        assert cloned.export() == identity.export()

    def test_clone_with_updates_overrides_fields(self):
        identity = _ConcreteIdentity(name="my_identity")
        cloned = identity.clone(name="cloned_identity")
        assert cloned.name == "cloned_identity"
        assert identity.name == "my_identity"

    def test_clone_deep_copies_mutable_tags(self):
        identity = _ConcreteIdentity(name="my_identity", tags={"env": "prod"})
        cloned = identity.clone()
        cloned.tags["env"] = "dev"
        assert identity.tags == {"env": "prod", "platform": Platform.LOCAL}


class TestBaseIdentityFromDict:
    def test_from_dict_builds_instance(self):
        identity = _ConcreteIdentity.from_dict({"name": "my_identity"})
        assert isinstance(identity, _ConcreteIdentity)
        assert identity.name == "my_identity"

    def test_from_dict_returns_same_instance_when_already_correct_type(self):
        identity = _ConcreteIdentity(name="my_identity")
        result = _ConcreteIdentity.from_dict(identity)
        assert result is identity


class TestBaseIdentityFromSetting:
    def test_from_setting_is_a_placeholder_returning_none(self):
        # BaseIdentity.from_setting is meant to be overridden by subclasses;
        # on the base class itself it is a no-op stub.
        settings = LocalIdentitySetting(name="my_identity")
        assert BaseIdentity.from_setting(settings) is None


class TestBaseIdentityDefault:
    def test_default_is_a_placeholder_returning_none(self):
        # BaseIdentity.default is meant to be overridden by subclasses;
        # on the base class itself it is a no-op stub.
        assert BaseIdentity.default() is None
