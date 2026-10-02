from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity
from app.resource.store.oss.store import OSSStore
from app.setting._store import OSSStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestOSSStoreInit:
    def test_missing_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSStore(name="my_store", region="cn-hangzhou")

    def test_missing_region_raises_validation_error(self):
        with pytest.raises(ValidationError):
            OSSStore(name="my_store", bucket="my-bucket")

    def test_default_identity_is_aliyun_identity_default(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        assert store.identity.name == AliyunIdentity.default().name

    def test_storesystem_and_platform_are_fixed(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        assert store.storesystem == StoreSystem.OSS
        assert store.platform == Platform.ALIYUN

    def test_default_prefix_is_store(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        assert store.prefix == "store"


class TestOSSStoreDerivePrefix:
    def test_trailing_slashes_are_stripped(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert store.prefix == "my/prefix"

    def test_none_prefix_becomes_store(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert store.prefix == "store"


class TestOSSStoreFromSetting:
    def test_from_setting_copies_bucket_region_prefix_in_vpc(self):
        setting = OSSStoreSetting(
            name="my_store",
            bucket="my-bucket",
            region="cn-hangzhou",
            prefix="my/prefix",
            in_vpc=True,
            tags={"env": "test"},
        )
        store = OSSStore.from_setting(setting)
        assert store.name == "my_store"
        assert store.bucket == "my-bucket"
        assert store.region == "cn-hangzhou"
        assert store.prefix == "my/prefix"
        assert store.in_vpc is True
        assert store.tags["env"] == "test"

    def test_from_setting_uses_default_identity_when_not_specified(self):
        setting = OSSStoreSetting(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        store = OSSStore.from_setting(setting)
        assert store.identity.name == AliyunIdentity.default().name

    def test_from_setting_resolves_named_identity(self):
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        setting = OSSStoreSetting(
            name="my_store",
            bucket="my-bucket",
            region="cn-hangzhou",
            identity="registered_aliyun_identity",
        )
        store = OSSStore.from_setting(setting)
        assert store.identity is _identity

    def test_from_setting_raises_value_error_on_platform_mismatch(self):
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        setting = OSSStoreSetting(
            name="my_store",
            bucket="my-bucket",
            region="cn-hangzhou",
            identity="a_local_identity",
        )
        with pytest.raises(ValueError):
            OSSStore.from_setting(setting)


class TestOSSStoreUri:
    def test_uri_returns_oss_scheme_with_bucket_and_prefix(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert store.uri == "oss://my-bucket/my/prefix"


class TestOSSStoreClient:
    def test_client_is_built_from_bucket_region_identity_in_vpc(self, monkeypatch):
        _captured = {}

        def _fake_get_client(**kwargs):
            _captured.update(kwargs)
            return MagicMock()

        monkeypatch.setattr(OSSClient, "get_client", _fake_get_client)
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", in_vpc=True)

        _ = store.client

        assert _captured["bucket"] == "my-bucket"
        assert _captured["region"] == "cn-hangzhou"
        assert _captured["identity"] is store.identity
        assert _captured["in_vpc"] is True


class TestOSSStoreWriteAndReadBytes:
    def test_write_bytes_calls_client_with_prefixed_key(self, monkeypatch):
        _fake_client = MagicMock()
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")

        store.write_bytes("a.txt", b"hello")

        _fake_client.write_bytes.assert_called_once_with("my/prefix/a.txt", b"hello")

    def test_read_bytes_calls_client_with_prefixed_key(self, monkeypatch):
        _fake_client = MagicMock(read_bytes=MagicMock(return_value=b"payload"))
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client)
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")

        result = store.read_bytes("a.txt")

        _fake_client.read_bytes.assert_called_once_with("my/prefix/a.txt")
        assert result == b"payload"


class TestOSSStoreFrn:
    def test_frn_returns_expected_identifier(self):
        store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        assert store.frn == f"store:platform={Platform.ALIYUN}:storesystem={StoreSystem.OSS}:name=my_store"
