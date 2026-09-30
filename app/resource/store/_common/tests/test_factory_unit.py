from __future__ import annotations

import pytest

from app.internal.constant.storesystem import StoreSystem
from app.resource._global.identities import GlobalIdentities
from app.resource.store._common._base import BaseStore
from app.resource.store._common._factory import StoreFactory
from app.resource.store.file.store import FileStore
from app.resource.store.oss.store import OSSStore
from app.setting._store import FileStoreSetting, OSSStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestStoreFactoryGet:
    def test_get_file_returns_file_store_class(self):
        klass = StoreFactory.get(StoreSystem.FILE)
        assert klass is FileStore

    def test_get_oss_returns_oss_store_class(self):
        klass = StoreFactory.get(StoreSystem.OSS)
        assert klass is OSSStore

    def test_get_accepts_plain_string_storesystem(self):
        klass = StoreFactory.get("file")
        assert klass is FileStore

    def test_get_returned_class_is_subclass_of_base_store(self):
        klass = StoreFactory.get(StoreSystem.OSS)
        assert issubclass(klass, BaseStore)

    def test_get_unknown_storesystem_raises_value_error(self):
        with pytest.raises(ValueError):
            StoreFactory.get("not_a_storesystem")


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
    def test_load_returns_file_store_instance(self, tmp_path):
        setting = FileStoreSetting(name="my_store", path=str(tmp_path))
        store = StoreFactory.load(setting)
        assert isinstance(store, FileStore)
        assert store.name == "my_store"

    def test_load_returns_oss_store_instance(self):
        setting = OSSStoreSetting(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        store = StoreFactory.load(setting)
        assert isinstance(store, OSSStore)
        assert store.name == "my_store"
        assert store.bucket == "my-bucket"

    def test_load_raises_value_error_when_get_returns_none(self, monkeypatch):
        monkeypatch.setattr(StoreFactory, "get", classmethod(lambda cls, storesystem: None))
        setting = FileStoreSetting(name="my_store")
        with pytest.raises(ValueError):
            StoreFactory.load(setting)
