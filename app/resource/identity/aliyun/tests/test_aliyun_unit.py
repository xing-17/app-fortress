from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.setting._identity import AliyunIdentitySetting


class TestAliyunIdentityInit:
    def test_default_type_is_chain(self):
        identity = AliyunIdentity(name="my_aliyun_identity")
        assert identity.type == AliyunIdentityType.CHAIN

    def test_default_keys_are_none(self):
        identity = AliyunIdentity(name="my_aliyun_identity")
        assert identity.access_key_id is None
        assert identity.access_key_secret is None

    def test_explicit_keys_are_kept(self):
        identity = AliyunIdentity(
            name="my_aliyun_identity",
            type=AliyunIdentityType.AK,
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
        )
        assert identity.access_key_id == "AKIDEXAMPLE"
        assert identity.access_key_secret == "secretvalue"

    def test_platform_is_fixed_to_aliyun(self):
        identity = AliyunIdentity(name="my_aliyun_identity")
        assert identity.platform == Platform.ALIYUN

    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AliyunIdentity()


class TestAliyunIdentityFromSetting:
    def test_from_setting_copies_name_type_and_tags(self):
        settings = AliyunIdentitySetting(
            name="my_aliyun_identity",
            type=AliyunIdentityType.AK,
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
            tags={"env": "test"},
        )
        identity = AliyunIdentity.from_setting(settings)
        assert identity.name == "my_aliyun_identity"
        assert identity.type == AliyunIdentityType.AK
        assert identity.tags == {"env": "test"}

    def test_from_setting_falls_back_to_static_keys(self):
        settings = AliyunIdentitySetting(
            name="my_aliyun_identity",
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
        )
        identity = AliyunIdentity.from_setting(settings)
        assert identity.access_key_id == "AKIDEXAMPLE"
        assert identity.access_key_secret == "secretvalue"

    def test_from_setting_prefers_env_var_over_static_key(self, monkeypatch):
        monkeypatch.setenv("FORTRESS_TEST_AK_ID", "AKIDFROMENV")
        settings = AliyunIdentitySetting(
            name="my_aliyun_identity",
            access_key_id="AKIDEXAMPLE",
            osenv_access_key_id="FORTRESS_TEST_AK_ID",
        )
        identity = AliyunIdentity.from_setting(settings)
        assert identity.access_key_id == "AKIDFROMENV"

    def test_from_setting_returns_aliyun_identity_instance(self):
        settings = AliyunIdentitySetting(name="my_aliyun_identity")
        identity = AliyunIdentity.from_setting(settings)
        assert isinstance(identity, AliyunIdentity)


class TestAliyunIdentityDescribe:
    def test_describe_masks_long_secret_keeping_last_four_chars(self):
        identity = AliyunIdentity(
            name="my_aliyun_identity",
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
        )
        result = json.loads(identity.describe())
        assert result["access_key_id"] == "*" * 7 + "MPLE"
        assert result["access_key_secret"] == "*" * 7 + "alue"

    def test_describe_masks_short_secret_entirely(self):
        identity = AliyunIdentity(name="my_aliyun_identity", access_key_id="ab")
        result = json.loads(identity.describe())
        assert result["access_key_id"] == "**"

    def test_describe_keeps_none_keys_as_none(self):
        identity = AliyunIdentity(name="my_aliyun_identity")
        result = json.loads(identity.describe())
        assert result["access_key_id"] is None
        assert result["access_key_secret"] is None

    def test_describe_does_not_mutate_original_instance(self):
        identity = AliyunIdentity(name="my_aliyun_identity", access_key_secret="secretvalue")
        identity.describe()
        assert identity.access_key_secret == "secretvalue"
