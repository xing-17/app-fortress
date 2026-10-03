from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.internal.constant.storesystem import StoreSystem
from app.resource._client.oss.client import OSSClient
from app.resource.store._common._factory import StoreFactory
from app.resource.store._common._store import BaseStore
from app.resource.store.file.store import FileStore
from app.resource.store.oss.store import OSSStore
from app.setting._store import FileStoreSetting, OSSStoreSetting


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
        setting = FileStoreSetting(name="my_store", path=str(tmp_path), tags={"env": "prod"})
        store = StoreFactory.load(setting)
        assert isinstance(store, FileStore)
        assert store.name == "my_store"

    def test_load_oss_returns_oss_store_instance(self, monkeypatch):
        _client = MagicMock()
        _client.list_folders.return_value = []
        monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
        setting = OSSStoreSetting(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        store = StoreFactory.load(setting)
        assert isinstance(store, OSSStore)
        assert store.name == "my_store"

    def test_load_raises_value_error_when_get_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(StoreFactory, "get", classmethod(lambda cls, storesystem: None))
        setting = FileStoreSetting(name="my_store", path=str(tmp_path))
        with pytest.raises(ValueError):
            StoreFactory.load(setting)
