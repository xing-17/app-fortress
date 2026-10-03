from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity
from app.resource.store.oss.database import OSSStoreDatabase
from app.resource.store.oss.store import OSSStore
from app.setting._store import OSSStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _fake_client(folders: list[dict] | None = None) -> MagicMock:
    _client = MagicMock()
    _client.list_folders.return_value = folders or []
    return _client


class TestOSSStoreInit:
    def test_missing_bucket_raises_validation_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        with pytest.raises(ValidationError):
            OSSStore(name="s", region="cn-hangzhou")

    def test_missing_region_raises_validation_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        with pytest.raises(ValidationError):
            OSSStore(name="s", bucket="my-bucket")

    def test_storesystem_and_platform_are_fixed(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert store.storesystem == StoreSystem.OSS
        assert store.platform == Platform.ALIYUN

    def test_default_identity_is_aliyun_identity_default(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert store.identity.name == AliyunIdentity.default().name

    def test_default_prefix_is_store(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert store.prefix == "store"

    def test_tags_include_name_storesystem_platform(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert store.tags["name"] == "s"
        assert store.tags["storesystem"] == StoreSystem.OSS
        assert store.tags["platform"] == Platform.ALIYUN


class TestOSSStoreDerivePrefix:
    def test_trailing_slashes_are_stripped(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix/")
        assert store.prefix == "my/prefix"

    def test_none_prefix_uses_default(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", prefix=None)
        assert store.prefix == "store"


class TestOSSStoreDeriveIdentity:
    def test_resolves_named_identity(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        _identity = AliyunIdentity(name="registered_aliyun_identity")
        GlobalIdentities.identities = {"registered_aliyun_identity": _identity}
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", identity="registered_aliyun_identity")
        assert store.identity is _identity

    def test_platform_mismatch_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        _local_identity = LocalIdentity(name="a_local_identity")
        GlobalIdentities.identities = {"a_local_identity": _local_identity}
        with pytest.raises(ValueError):
            OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", identity="a_local_identity")


class TestOSSStoreUri:
    def test_uri_returns_oss_scheme_with_bucket_and_prefix(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        assert store.uri == "oss://my-bucket/my/prefix"


class TestOSSStoreClient:
    def test_client_property_resolves_via_oss_client_get_client(self, monkeypatch):
        _captured = {}
        _client = _fake_client()

        def _fake_get_client(**kwargs):
            _captured.update(kwargs)
            return _client

        monkeypatch.setattr(OSSClient, "get_client", _fake_get_client)
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", in_vpc=True)
        assert store.client is _client
        assert _captured == {
            "bucket": "my-bucket",
            "region": "cn-hangzhou",
            "identity": store.identity,
            "in_vpc": True,
        }


class TestOSSStoreDeriveDatabases:
    def test_eager_databases_empty_when_no_folders(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client(folders=[]))
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert store.databases == []

    def test_eager_databases_populated_from_folders(self, monkeypatch):
        monkeypatch.setattr(
            OSSClient,
            "get_client",
            lambda **kwargs: _fake_client(folders=[{"bucket": "my-bucket", "prefix": "store/db_a/"}]),
        )
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert [d.name for d in store.databases] == ["db_a"]

    def test_databases_property_is_already_cached_right_after_construction(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        monkeypatch.setattr(OSSStore, "list_databases", MagicMock())
        assert store.databases == []
        store.list_databases.assert_not_called()


class TestOSSStoreFromSetting:
    def test_builds_store_from_setting_fields(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        _setting = OSSStoreSetting(name="s", bucket="my-bucket", region="cn-hangzhou", tags={"env": "prod"})
        store = OSSStore.from_setting(_setting)
        assert store.name == "s"
        assert store.bucket == "my-bucket"
        assert store.region == "cn-hangzhou"
        assert store.tags["env"] == "prod"


class TestOSSStoreListDatabases:
    def test_name_is_derived_from_common_prefix(self, monkeypatch):
        monkeypatch.setattr(
            OSSClient,
            "get_client",
            lambda **kwargs: _fake_client(folders=[{"bucket": "my-bucket", "prefix": "store/db_a/"}]),
        )
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        assert [d.name for d in store.list_databases()] == ["db_a"]

    def test_database_inherits_store_identity_bucket_region(self, monkeypatch):
        monkeypatch.setattr(
            OSSClient,
            "get_client",
            lambda **kwargs: _fake_client(folders=[{"bucket": "my-bucket", "prefix": "store/db_a/"}]),
        )
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        _db = store.list_databases()[0]
        assert _db.identity is store.identity
        assert _db.bucket == store.bucket
        assert _db.region == store.region

    def test_forwards_prefix_and_recursive_to_client(self, monkeypatch):
        _captured = {}

        def _fake_list_folders(**kwargs):
            _captured.update(kwargs)
            return []

        _client = _fake_client()
        _client.list_folders.side_effect = _fake_list_folders
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", prefix="my/prefix")
        store.list_databases()
        assert _captured == {
            "prefix": "my/prefix",
            "recursive": False,
        }


class TestOSSStoreDatabaseMethod:
    def test_creates_database_with_given_name_under_store_prefix(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", prefix="store")
        db = store.database("newdb")
        assert isinstance(db, OSSStoreDatabase)
        assert db.prefix == "store/newdb"

    def test_database_inherits_store_identity(self, monkeypatch):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        db = store.database("newdb")
        assert db.identity is store.identity

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, monkeypatch, bad_name):
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _fake_client())
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
        with pytest.raises(ValidationError):
            store.database(bad_name)
