from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity._common._identitysecret import BaseIdentitySecret


class _ConcreteSecret(BaseIdentitySecret):
    platform: ClassVar[Platform] = Platform.LOCAL


class TestBaseSecret:
    def test_platform_comes_from_subclass(self):
        assert _ConcreteSecret().platform == Platform.LOCAL

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            _ConcreteSecret(unknown="x")

    def test_identity_must_implement_as_secret(self):
        class _NoSecretIdentity(BaseIdentity):
            platform: ClassVar[Platform] = Platform.LOCAL

            @classmethod
            def from_setting(cls, setting):
                return cls(name=setting.name)

            @classmethod
            def default(cls):
                return cls(name="x")

        with pytest.raises(TypeError):
            _NoSecretIdentity(name="x")
