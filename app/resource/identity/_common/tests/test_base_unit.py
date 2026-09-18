from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity
from app.setting._identity import LocalIdentitySetting


class TestBaseIdentityInit:
    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BaseIdentity()

    def test_default_platform_is_local(self):
        identity = BaseIdentity(name="my_identity")
        assert identity.platform == Platform.LOCAL

    def test_default_tags_is_empty_dict(self):
        identity = BaseIdentity(name="my_identity")
        assert identity.tags == {}

    def test_tags_default_factory_is_independent_per_instance(self):
        first = BaseIdentity(name="first")
        second = BaseIdentity(name="second")
        first.tags["env"] = "prod"
        assert second.tags == {}

    def test_explicit_platform_and_tags_are_kept(self):
        identity = BaseIdentity(name="my_identity", platform=Platform.ALIYUN, tags={"env": "prod"})
        assert identity.platform == Platform.ALIYUN
        assert identity.tags == {"env": "prod"}


class TestBaseIdentityExport:
    def test_export_returns_expected_dict(self):
        identity = BaseIdentity(name="my_identity", tags={"env": "prod"})
        result = identity.export()
        assert result == {
            "name": "my_identity",
            "platform": Platform.LOCAL.value,
            "tags": {"env": "prod"},
        }

    def test_describe_returns_valid_json_matching_export(self):
        identity = BaseIdentity(name="my_identity")
        assert json.loads(identity.describe()) == identity.export()


class TestBaseIdentityClone:
    def test_clone_without_updates_produces_equal_copy(self):
        identity = BaseIdentity(name="my_identity", tags={"env": "prod"})
        cloned = identity.clone()
        assert cloned is not identity
        assert cloned.export() == identity.export()

    def test_clone_with_updates_overrides_fields(self):
        identity = BaseIdentity(name="my_identity")
        cloned = identity.clone(name="cloned_identity")
        assert cloned.name == "cloned_identity"
        assert identity.name == "my_identity"

    def test_clone_deep_copies_mutable_tags(self):
        identity = BaseIdentity(name="my_identity", tags={"env": "prod"})
        cloned = identity.clone()
        cloned.tags["env"] = "dev"
        assert identity.tags == {"env": "prod"}


class TestBaseIdentityFromDict:
    def test_from_dict_builds_instance(self):
        identity = BaseIdentity.from_dict({"name": "my_identity"})
        assert isinstance(identity, BaseIdentity)
        assert identity.name == "my_identity"

    def test_from_dict_returns_same_instance_when_already_correct_type(self):
        identity = BaseIdentity(name="my_identity")
        result = BaseIdentity.from_dict(identity)
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
