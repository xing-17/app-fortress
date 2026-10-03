from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity.local.identity import LocalIdentity
from app.setting._identity import LocalIdentitySetting


class TestLocalIdentityInit:
    def test_platform_is_fixed_to_local(self):
        identity = LocalIdentity(name="my_local_identity")
        assert identity.platform == Platform.LOCAL

    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LocalIdentity()


class TestLocalIdentityFromSetting:
    def test_from_setting_copies_name_and_tags(self):
        settings = LocalIdentitySetting(name="my_local_identity", tags={"env": "test"})
        identity = LocalIdentity.from_setting(settings)
        assert identity.name == "my_local_identity"

    def test_from_setting_returns_local_identity_instance(self):
        settings = LocalIdentitySetting(name="my_local_identity")
        identity = LocalIdentity.from_setting(settings)
        assert isinstance(identity, LocalIdentity)


class TestLocalIdentityDefault:
    def test_default_returns_local_identity_instance(self):
        identity = LocalIdentity.default()
        assert isinstance(identity, LocalIdentity)

    def test_default_name_and_tags(self):
        identity = LocalIdentity.default()
        assert identity.name == "local_default_identity"
        assert identity.tags == {"platform": "local"}

    def test_default_platform_is_local(self):
        identity = LocalIdentity.default()
        assert identity.platform == Platform.LOCAL

    def test_default_returns_new_instance_each_call(self):
        first = LocalIdentity.default()
        second = LocalIdentity.default()
        assert first is not second
        first.tags["env"] = "prod"
        assert second.tags == {"platform": "local"}


class TestLocalIdentityDescribe:
    def test_describe_is_valid_json(self):
        identity = LocalIdentity(name="my_local_identity", tags={"env": "production"})
        result = json.loads(identity.describe())
        assert result["name"] == "my_local_identity"
        assert result["tags"] == {"env": "production", "platform": Platform.LOCAL.value}
        assert result["platform"] == Platform.LOCAL
