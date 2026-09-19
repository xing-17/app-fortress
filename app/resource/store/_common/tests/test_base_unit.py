from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource.store._common._base import BaseStore
from app.setting._store import LocalStoreSetting


class TestBaseStoreInit:
    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BaseStore()

    def test_default_platform_is_local(self):
        store = BaseStore(name="my_store")
        assert store.platform == Platform.LOCAL

    def test_default_tags_is_empty_dict(self):
        store = BaseStore(name="my_store")
        assert store.tags == {}

    def test_tags_default_factory_is_independent_per_instance(self):
        first = BaseStore(name="first")
        second = BaseStore(name="second")
        first.tags["env"] = "prod"
        assert second.tags == {}

    def test_explicit_platform_and_tags_are_kept(self):
        store = BaseStore(name="my_store", platform=Platform.ALIYUN, tags={"env": "prod"})
        assert store.platform == Platform.ALIYUN
        assert store.tags == {"env": "prod"}


class TestBaseStoreExport:
    def test_export_returns_expected_dict(self):
        store = BaseStore(name="my_store", tags={"env": "prod"})
        result = store.export()
        assert result == {
            "name": "my_store",
            "platform": Platform.LOCAL.value,
            "tags": {"env": "prod"},
        }

    def test_describe_returns_valid_json_matching_export(self):
        store = BaseStore(name="my_store")
        assert json.loads(store.describe()) == store.export()


class TestBaseStoreClone:
    def test_clone_without_updates_produces_equal_copy(self):
        store = BaseStore(name="my_store", tags={"env": "prod"})
        cloned = store.clone()
        assert cloned is not store
        assert cloned.export() == store.export()

    def test_clone_with_updates_overrides_fields(self):
        store = BaseStore(name="my_store")
        cloned = store.clone(name="cloned_store")
        assert cloned.name == "cloned_store"
        assert store.name == "my_store"

    def test_clone_deep_copies_mutable_tags(self):
        store = BaseStore(name="my_store", tags={"env": "prod"})
        cloned = store.clone()
        cloned.tags["env"] = "dev"
        assert store.tags == {"env": "prod"}


class TestBaseStoreFromDict:
    def test_from_dict_builds_instance(self):
        store = BaseStore.from_dict({"name": "my_store"})
        assert isinstance(store, BaseStore)
        assert store.name == "my_store"

    def test_from_dict_returns_same_instance_when_already_correct_type(self):
        store = BaseStore(name="my_store")
        result = BaseStore.from_dict(store)
        assert result is store


class TestBaseStoreFromSetting:
    def test_from_setting_is_a_placeholder_returning_none(self):
        # BaseStore.from_setting is meant to be overridden by subclasses;
        # on the base class itself it is a no-op stub.
        settings = LocalStoreSetting(name="my_store", tags={})
        assert BaseStore.from_setting(settings) is None
