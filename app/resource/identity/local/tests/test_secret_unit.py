from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity.local.identity import LocalIdentity
from app.resource.identity.local.secret import LocalSecret


class TestLocalSecret:
    def test_platform_is_fixed_to_local(self):
        assert LocalSecret().platform == Platform.LOCAL

    def test_export_is_empty(self):
        assert LocalSecret().export() == {}

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            LocalSecret(access_key_id="x")


class TestLocalIdentityAsSecret:
    def test_returns_empty_local_secret(self):
        _secret = LocalIdentity.default().as_secret()
        assert isinstance(_secret, LocalSecret)
