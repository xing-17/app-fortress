from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity.local.local import LocalIdentity
from app.setting._identity import LocalIdentitySetting


class TestLocalIdentityInit:
    def test_default_tags_is_empty_dict(self):
        identity = LocalIdentity(name="my_local_identity")
        assert identity.tags == {}

    def test_explicit_tags_are_kept(self):
        identity = LocalIdentity(name="my_local_identity", tags={"env": "production"})
        assert identity.tags == {"env": "production"}

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
        assert identity.tags == {"env": "test"}

    def test_from_setting_returns_local_identity_instance(self):
        settings = LocalIdentitySetting(name="my_local_identity")
        identity = LocalIdentity.from_setting(settings)
        assert isinstance(identity, LocalIdentity)


class TestLocalIdentityDescribe:
    def test_describe_is_valid_json(self):
        identity = LocalIdentity(name="my_local_identity", tags={"env": "production"})
        result = json.loads(identity.describe())
        assert result["name"] == "my_local_identity"
        assert result["tags"] == {"env": "production"}
        assert result["platform"] == Platform.LOCAL
