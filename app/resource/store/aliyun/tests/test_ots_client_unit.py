from __future__ import annotations

from unittest.mock import MagicMock

from alibabacloud_credentials.models import CredentialModel

from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.store.aliyun import _client as ots_client_module
from app.resource.store.aliyun._client import OTSClient


def _make_identity(name: str = "my-identity") -> AliyunIdentity:
    return AliyunIdentity(name=name)


class TestOTSClientInit:
    def test_stores_endpoint_region_instance_identity(self):
        identity = _make_identity()
        client = OTSClient(
            endpoint="https://my-instance.cn-hangzhou.ots.aliyuncs.com",
            region="cn-hangzhou",
            instance="my-instance",
            identity=identity,
        )
        assert client.endpoint == "https://my-instance.cn-hangzhou.ots.aliyuncs.com"
        assert client.region == "cn-hangzhou"
        assert client.instance == "my-instance"
        assert client.identity is identity

    def test_lazy_client_is_none_until_accessed(self):
        client = OTSClient(
            endpoint="https://my-instance.cn-hangzhou.ots.aliyuncs.com",
            region="cn-hangzhou",
            instance="my-instance",
            identity=_make_identity(),
        )
        assert client._client is None


class TestOTSClientProperty:
    def test_client_is_built_from_identity_credential(self, monkeypatch):
        _cred = CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        _mock_client_cls = MagicMock()
        monkeypatch.setattr(ots_client_module, "OTSTeaClient", _mock_client_cls)

        identity = _make_identity()
        monkeypatch.setattr(AliyunIdentity, "get_credential", MagicMock(return_value=_cred))
        client = OTSClient(
            endpoint="https://my-instance.cn-hangzhou.ots.aliyuncs.com",
            region="cn-hangzhou",
            instance="my-instance",
            identity=identity,
        )

        result = client.client

        _mock_client_cls.assert_called_once_with(
            end_point=client.endpoint,
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
            region="cn-hangzhou",
            instance_name="my-instance",
        )
        assert result is _mock_client_cls.return_value

    def test_client_is_cached_across_calls(self, monkeypatch):
        _cred = CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        _mock_client_cls = MagicMock()
        monkeypatch.setattr(ots_client_module, "OTSTeaClient", _mock_client_cls)

        identity = _make_identity()
        monkeypatch.setattr(AliyunIdentity, "get_credential", MagicMock(return_value=_cred))
        client = OTSClient(
            endpoint="https://my-instance.cn-hangzhou.ots.aliyuncs.com",
            region="cn-hangzhou",
            instance="my-instance",
            identity=identity,
        )

        first = client.client
        second = client.client

        assert first is second
        _mock_client_cls.assert_called_once()
