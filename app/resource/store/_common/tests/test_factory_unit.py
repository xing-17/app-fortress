from __future__ import annotations

import pytest

from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.store._common._base import BaseStore
from app.resource.store._common._factory import StoreFactory
from app.resource.store.aliyun.ots import OtsStore
from app.resource.store.local.duckdb import DuckDbStore
from app.setting._store import AliyunStoreSetting, LocalStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestStoreFactoryGet:
    def test_get_local_returns_duckdb_store_class(self):
        klass = StoreFactory.get(Platform.LOCAL)
        assert klass is DuckDbStore

    def test_get_aliyun_returns_ots_store_class(self):
        klass = StoreFactory.get(Platform.ALIYUN)
        assert klass is OtsStore

    def test_get_accepts_plain_string_platform(self):
        klass = StoreFactory.get("local")
        assert klass is DuckDbStore

    def test_get_returned_class_is_subclass_of_base_store(self):
        klass = StoreFactory.get(Platform.ALIYUN)
        assert issubclass(klass, BaseStore)

    def test_get_unknown_platform_raises_value_error(self):
        with pytest.raises(ValueError):
            StoreFactory.get("not_a_platform")


class TestStoreFactoryRegistryValidation:
    def test_get_raises_type_error_when_target_is_not_a_class(self, monkeypatch):
        monkeypatch.setitem(StoreFactory._registry, "not_a_class", "os:getcwd")
        with pytest.raises(TypeError):
            StoreFactory.get("not_a_class")

    def test_get_raises_type_error_when_target_is_not_base_store_subclass(self, monkeypatch):
        monkeypatch.setitem(
            StoreFactory._registry,
            "not_base_store",
            "app.resource.store._common._factory:StoreFactory",
        )
        with pytest.raises(TypeError):
            StoreFactory.get("not_base_store")


class TestStoreFactoryLoad:
    def test_load_returns_duckdb_store_instance(self, tmp_path):
        GlobalIdentities.identities = {}
        setting = LocalStoreSetting(
            name="my-duckdb-store",
            path=str(tmp_path),
            tags={"env": "prod"},
        )
        store = StoreFactory.load(setting)
        assert isinstance(store, DuckDbStore)
        assert store.name == "my-duckdb-store"

    def test_load_returns_ots_store_instance(self):
        GlobalIdentities.identities = {}
        setting = AliyunStoreSetting(
            name="my-ots-store",
            instance="my-instance",
            region="cn-hangzhou",
            tags={},
        )
        store = StoreFactory.load(setting)
        assert isinstance(store, OtsStore)
        assert store.name == "my-ots-store"
        assert store.instance == "my-instance"

    def test_load_raises_value_error_when_get_returns_none(self, monkeypatch):
        GlobalIdentities.identities = {}
        monkeypatch.setattr(StoreFactory, "get", classmethod(lambda cls, platform: None))
        setting = LocalStoreSetting(name="my-duckdb-store", tags={})
        with pytest.raises(ValueError):
            StoreFactory.load(setting)
