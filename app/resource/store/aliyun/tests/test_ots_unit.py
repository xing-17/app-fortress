from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from alibabacloud_credentials.models import CredentialModel
from pydantic import ValidationError
from urllib3.exceptions import MaxRetryError, NameResolutionError

from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store.aliyun import ots as ots_module
from app.resource.store.aliyun.ots import OtsStore
from app.setting._store import AliyunStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOtsStoreInit:
    def test_missing_required_fields_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OtsStore(name="my-ots-store")

    def test_platform_is_fixed_to_aliyun(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        assert store.platform == Platform.ALIYUN

    def test_default_in_vpc_is_false(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        assert store.in_vpc is False

    def test_default_identity_is_aliyun_default(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        assert store.identity.name == AliyunIdentity.default().name

    def test_default_tags_is_empty_dict(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        assert store.tags == {}


class TestOtsStoreDeriveEndpoint:
    def test_public_endpoint_when_not_in_vpc(self):
        store = OtsStore(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            in_vpc=False,
        )
        assert store.endpoint == "https://my-instance.cn-hangzhou.ots.aliyuncs.com"

    def test_internal_endpoint_when_in_vpc(self):
        store = OtsStore(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            in_vpc=True,
        )
        assert store.endpoint == "https://my-instance.cn-hangzhou.ots-internal.aliyuncs.com"

    def test_explicit_endpoint_is_kept(self):
        store = OtsStore(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            endpoint="https://custom.endpoint.example.com",
        )
        assert store.endpoint == "https://custom.endpoint.example.com"


class TestOtsStoreFromSetting:
    def test_from_setting_copies_basic_fields(self):
        setting = AliyunStoreSetting(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            in_vpc=True,
            tags={"env": "test"},
        )
        store = OtsStore.from_setting(setting)
        assert store.name == "my-ots-store"
        assert store.instance == "my-instance"
        assert store.region == "cn-hangzhou"
        assert store.in_vpc is True

    def test_from_setting_resolves_registered_identity(self):
        identity = AliyunIdentity(name="my-identity")
        GlobalIdentities.identities = {"my-identity": identity}
        setting = AliyunStoreSetting(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            identity="my-identity",
            tags={},
        )
        store = OtsStore.from_setting(setting)
        assert store.identity is identity

    def test_from_setting_falls_back_to_default_identity_when_not_registered(self):
        GlobalIdentities.identities = {}
        setting = AliyunStoreSetting(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            identity="missing-identity",
            tags={},
        )
        store = OtsStore.from_setting(setting)
        assert store.identity.name == AliyunIdentity.default().name

    def test_from_setting_returns_ots_store_instance(self):
        setting = AliyunStoreSetting(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            tags={},
        )
        store = OtsStore.from_setting(setting)
        assert isinstance(store, OtsStore)


class TestOtsStoreClient:
    def test_client_is_built_from_identity_credential(self, monkeypatch):
        _cred = CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        _mock_client_cls = MagicMock()
        monkeypatch.setattr(ots_module, "OTSClient", _mock_client_cls)

        identity = AliyunIdentity(name="my-identity")
        monkeypatch.setattr(AliyunIdentity, "get_credential", MagicMock(return_value=_cred))
        store = OtsStore(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            identity=identity,
        )

        result = store.client

        _mock_client_cls.assert_called_once_with(
            end_point=store.endpoint,
            access_key_id="AKIDEXAMPLE",
            access_key_secret="secretvalue",
            region="cn-hangzhou",
            instance_name="my-instance",
        )
        assert result is _mock_client_cls.return_value

    def test_client_is_cached_across_calls(self, monkeypatch):
        _cred = CredentialModel(access_key_id="AKIDEXAMPLE", access_key_secret="secretvalue")
        _mock_client_cls = MagicMock()
        monkeypatch.setattr(ots_module, "OTSClient", _mock_client_cls)

        identity = AliyunIdentity(name="my-identity")
        monkeypatch.setattr(AliyunIdentity, "get_credential", MagicMock(return_value=_cred))
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou", identity=identity)

        first = store.client
        second = store.client

        assert first is second
        _mock_client_cls.assert_called_once()


class TestOtsStoreInstanceExists:
    def test_returns_true_when_list_table_succeeds(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        store._client = MagicMock(list_table=MagicMock(return_value=None))
        assert store.instance_exists() is True

    def test_returns_false_on_max_retry_error(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        store._client = MagicMock(list_table=MagicMock(side_effect=MaxRetryError(pool=None, url="/")))
        assert store.instance_exists() is False

    def test_returns_false_on_name_resolution_error(self):
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou")
        store._client = MagicMock(
            list_table=MagicMock(side_effect=NameResolutionError(host="my-instance", conn=None, reason=None))
        )
        assert store.instance_exists() is False


class TestOtsStoreExport:
    def test_export_replaces_identity_with_name(self):
        identity = AliyunIdentity(name="my-identity")
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou", identity=identity)
        result = store.export()
        assert result["identity"] == "my-identity"

    def test_describe_is_valid_json_containing_identity_name(self):
        identity = AliyunIdentity(name="my-identity")
        store = OtsStore(name="my-ots-store", instance="my-instance", region="cn-hangzhou", identity=identity)
        result = json.loads(store.describe())
        assert result["identity"] == "my-identity"
