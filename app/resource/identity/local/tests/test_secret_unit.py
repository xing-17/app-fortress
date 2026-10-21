from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity.local.identity import LocalIdentity
from app.resource.identity.local.identitysecret import LocalIdentitySecret


class TestLocalSecret:
    def test_platform_is_fixed_to_local(self):
        assert LocalIdentitySecret().platform == Platform.LOCAL

    def test_export_is_empty(self):
        assert LocalIdentitySecret().export() == {}

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            LocalIdentitySecret(access_key_id="x")


class TestLocalIdentityAsSecret:
    def test_returns_empty_local_secret(self):
        _secret = LocalIdentity.default().as_secret()
        assert isinstance(_secret, LocalIdentitySecret)
