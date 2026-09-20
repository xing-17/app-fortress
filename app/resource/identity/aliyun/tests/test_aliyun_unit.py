from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from alibabacloud_credentials.models import CredentialModel
from pydantic import ValidationError

from app.internal.constant.aliyunidentitytype import AliyunIdentityType
from app.internal.constant.platform import Platform
from app.resource.identity.aliyun import aliyun as aliyun_module
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


class TestAliyunIdentityDefault:
    def test_default_returns_aliyun_identity_instance(self):
        identity = AliyunIdentity.default()
        assert isinstance(identity, AliyunIdentity)

    def test_default_uses_chain_type_and_no_keys(self):
        identity = AliyunIdentity.default()
        assert identity.type == AliyunIdentityType.CHAIN
        assert identity.access_key_id is None
        assert identity.access_key_secret is None

    def test_default_name_and_tags(self):
        identity = AliyunIdentity.default()
        assert identity.name == "aliyun_default_identity"
        assert identity.tags == {
            "platform": "aliyun",
            "type": "chain",
            "name": "aliyun_default_identity",
            "source": "auto_generated",
        }

    def test_default_platform_is_aliyun(self):
        identity = AliyunIdentity.default()
        assert identity.platform == Platform.ALIYUN

    def test_default_returns_new_instance_each_call(self):
        first = AliyunIdentity.default()
        second = AliyunIdentity.default()
        assert first is not second
        first.tags["env"] = "prod"
        assert second.tags == {
            "platform": "aliyun",
            "type": "chain",
            "name": "aliyun_default_identity",
            "source": "auto_generated",
        }


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


class TestAliyunIdentityGetCredential:
    def test_chain_type_uses_default_credential_client_with_no_config(self, monkeypatch):
        _expected = CredentialModel(access_key_id="chain_ak", access_key_secret="chain_sk")
        _mock_client_cls = MagicMock(return_value=MagicMock(get_credential=MagicMock(return_value=_expected)))
        monkeypatch.setattr(aliyun_module, "CredentialClient", _mock_client_cls)

        identity = AliyunIdentity(name="my_aliyun_identity", type=AliyunIdentityType.CHAIN)
        result = identity.get_credential()

        _mock_client_cls.assert_called_once_with()
        assert result is _expected

    def test_ak_type_builds_config_from_keys_and_returns_credential(self, monkeypatch):
        _expected = CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        _mock_client_cls = MagicMock(return_value=MagicMock(get_credential=MagicMock(return_value=_expected)))
        _mock_config_cls = MagicMock()
        monkeypatch.setattr(aliyun_module, "CredentialClient", _mock_client_cls)
        monkeypatch.setattr(aliyun_module, "CredentialConfig", _mock_config_cls)

        identity = AliyunIdentity(
            name="my_aliyun_identity",
            type=AliyunIdentityType.AK,
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
        )
        result = identity.get_credential()

        _mock_config_cls.assert_called_once_with(
            type="access_key",
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
        )
        _mock_client_cls.assert_called_once_with(_mock_config_cls.return_value)
        assert result is _expected

    def test_ak_type_missing_access_key_id_raises_value_error(self):
        identity = AliyunIdentity(
            name="my_aliyun_identity",
            type=AliyunIdentityType.AK,
            access_key_secret="secretvalue",
        )
        with pytest.raises(ValueError, match="Access key ID and Secret"):
            identity.get_credential()

    def test_ak_type_missing_access_key_secret_raises_value_error(self):
        identity = AliyunIdentity(
            name="my_aliyun_identity",
            type=AliyunIdentityType.AK,
            access_key_id="AKIDEXAMPLE",
        )
        with pytest.raises(ValueError, match="Access key ID and Secret"):
            identity.get_credential()

    def test_unsupported_type_raises_value_error(self):
        identity = AliyunIdentity(name="my_aliyun_identity")
        # Bypass pydantic's validate_assignment to force an out-of-enum value.
        object.__setattr__(identity, "type", "not_a_real_type")
        with pytest.raises(ValueError, match="Unsupported Aliyun identity type"):
            identity.get_credential()
