from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from alibabacloud_credentials.client import CredentialModel
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.aliyun.identitysecret import AliyunIdentitySecret

_SECRET = "secretvalue-123456"
_TOKEN = "tokenvalue-654321"


class TestAliyunIdentitySecret:
    def test_platform_is_fixed_to_aliyun(self):
        _secret = AliyunIdentitySecret(access_key_id="AKID", access_key_secret=_SECRET)
        assert _secret.platform == Platform.ALIYUN

    def test_missing_secret_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AliyunIdentitySecret(access_key_id="AKID")

    def test_security_token_defaults_to_none(self):
        _secret = AliyunIdentitySecret(access_key_id="AKID", access_key_secret=_SECRET)
        assert _secret.security_token is None

    def test_values_are_readable_only_through_get_secret_value(self):
        _secret = AliyunIdentitySecret(
            access_key_id="AKID",
            access_key_secret=_SECRET,
            security_token=_TOKEN,
        )
        assert _secret.access_key_secret.get_secret_value() == _SECRET
        assert _secret.security_token.get_secret_value() == _TOKEN

    def test_instance_is_frozen(self):
        _secret = AliyunIdentitySecret(access_key_id="AKID", access_key_secret=_SECRET)
        with pytest.raises(ValidationError):
            _secret.access_key_id = "other"

    def test_values_do_not_leak_through_repr_export_or_describe(self):
        _secret = AliyunIdentitySecret(
            access_key_id="AKID",
            access_key_secret=_SECRET,
            security_token=_TOKEN,
        )
        _texts = [
            repr(_secret),
            str(_secret),
            _secret.describe(),
            str(_secret.export()),
            _secret.model_dump_json(),
        ]
        for _text in _texts:
            assert _SECRET not in _text
            assert _TOKEN not in _text


class TestAliyunIdentityAsSecret:
    @pytest.fixture(autouse=True)
    def _clear_credential_clients(self):
        AliyunIdentity._credential_clients.clear()
        yield
        AliyunIdentity._credential_clients.clear()

    def _patch_client(self, monkeypatch, *models: CredentialModel) -> MagicMock:
        _client = MagicMock()
        _client.get_credential.side_effect = list(models)
        monkeypatch.setattr(AliyunIdentity, "get_client", MagicMock(return_value=_client))
        return _client

    def test_converts_sdk_credential_into_aliyun_secret(self, monkeypatch):
        self._patch_client(
            monkeypatch,
            CredentialModel(access_key_id="AKID", access_key_secret=_SECRET, security_token=_TOKEN),
        )
        _secret = AliyunIdentity(name="n").as_secret()
        assert isinstance(_secret, AliyunIdentitySecret)
        assert _secret.access_key_id == "AKID"
        assert _secret.access_key_secret.get_secret_value() == _SECRET
        assert _secret.security_token.get_secret_value() == _TOKEN

    def test_long_lived_key_has_no_security_token(self, monkeypatch):
        self._patch_client(
            monkeypatch,
            CredentialModel(access_key_id="AKID", access_key_secret=_SECRET, security_token=""),
        )
        assert AliyunIdentity(name="n").as_secret().security_token is None

    def test_every_call_produces_a_fresh_secret(self, monkeypatch):
        _client = self._patch_client(
            monkeypatch,
            CredentialModel(access_key_id="AKID1", access_key_secret=_SECRET, security_token=_TOKEN),
            CredentialModel(access_key_id="AKID2", access_key_secret=_SECRET, security_token=_TOKEN),
        )
        _identity = AliyunIdentity(name="n")
        assert _identity.as_secret().access_key_id == "AKID1"
        assert _identity.as_secret().access_key_id == "AKID2"
        assert _client.get_credential.call_count == 2
