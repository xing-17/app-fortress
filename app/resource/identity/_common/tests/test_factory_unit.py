from __future__ import annotations

import pytest

from app.internal.constant.platform import Platform
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity._common._factory import IdentityFactory
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity
from app.setting._identity import AliyunIdentitySetting, LocalIdentitySetting


class TestIdentityFactoryGet:
    def test_get_local_returns_local_identity_class(self):
        klass = IdentityFactory.get(Platform.LOCAL)
        assert klass is LocalIdentity

    def test_get_aliyun_returns_aliyun_identity_class(self):
        klass = IdentityFactory.get(Platform.ALIYUN)
        assert klass is AliyunIdentity

    def test_get_accepts_plain_string_platform(self):
        klass = IdentityFactory.get("local")
        assert klass is LocalIdentity

    def test_get_returned_class_is_subclass_of_base_identity(self):
        klass = IdentityFactory.get(Platform.ALIYUN)
        assert issubclass(klass, BaseIdentity)

    def test_get_unknown_platform_raises_value_error(self):
        with pytest.raises(ValueError):
            IdentityFactory.get("not_a_platform")


class TestIdentityFactoryRegistryValidation:
    def test_get_raises_type_error_when_target_is_not_a_class(self, monkeypatch):
        monkeypatch.setitem(IdentityFactory._registry, "not_a_class", "os:getcwd")
        with pytest.raises(TypeError):
            IdentityFactory.get("not_a_class")

    def test_get_raises_type_error_when_target_is_not_base_identity_subclass(self, monkeypatch):
        monkeypatch.setitem(
            IdentityFactory._registry,
            "not_base_identity",
            "app.resource.identity._common._factory:IdentityFactory",
        )
        with pytest.raises(TypeError):
            IdentityFactory.get("not_base_identity")


class TestIdentityFactoryDefault:
    @pytest.mark.parametrize("platform", [Platform.LOCAL, Platform.ALIYUN])
    def test_get_klass_default_returns_matching_identity_instance(self, platform):
        klass = IdentityFactory.get(platform)
        identity = klass.default()
        assert isinstance(identity, klass)
        assert identity.platform == platform


class TestIdentityFactoryLoad:
    def test_load_returns_local_identity_instance(self):
        setting = LocalIdentitySetting(name="my_identity", tags={"env": "prod"})
        identity = IdentityFactory.load(setting)
        assert isinstance(identity, LocalIdentity)
        assert identity.name == "my_identity"

    def test_load_returns_aliyun_identity_instance(self):
        setting = AliyunIdentitySetting(
            name="my_identity",
            access_key_id="ak_id",
            access_key_secret="ak_secret",
        )
        identity = IdentityFactory.load(setting)
        assert isinstance(identity, AliyunIdentity)
        assert identity.name == "my_identity"
        assert identity.access_key_id == "ak_id"
        assert identity.access_key_secret == "ak_secret"

    def test_load_raises_value_error_when_get_returns_none(self, monkeypatch):
        monkeypatch.setattr(IdentityFactory, "get", classmethod(lambda cls, platform: None))
        setting = LocalIdentitySetting(name="my_identity")
        with pytest.raises(ValueError):
            IdentityFactory.load(setting)
