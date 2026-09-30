from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.identity.local.local import LocalIdentity
from app.resource.store._common._base import BaseStore
from app.setting._store import FileStoreSetting


class TestBaseStoreInit:
    def test_missing_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BaseStore(storesystem=StoreSystem.FILE, platform=Platform.LOCAL)

    def test_missing_storesystem_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BaseStore(name="my_store", platform=Platform.LOCAL)

    def test_missing_platform_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BaseStore(name="my_store", storesystem=StoreSystem.FILE)

    def test_default_identity_is_none(self):
        store = BaseStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.identity is None

    def test_default_tags_contain_only_non_override_keys(self):
        store = BaseStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.tags == {
            "storesystem": StoreSystem.FILE,
            "platform": Platform.LOCAL,
            "name": "my_store",
        }

    def test_tags_default_factory_is_independent_per_instance(self):
        first = BaseStore(name="first", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        second = BaseStore(name="second", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        first.tags["env"] = "prod"
        assert "env" not in second.tags

    def test_explicit_tags_are_merged_with_non_override_tags(self):
        store = BaseStore(
            name="my_store",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            tags={"env": "prod"},
        )
        assert store.tags == {
            "env": "prod",
            "storesystem": StoreSystem.FILE,
            "platform": Platform.LOCAL,
            "name": "my_store",
        }


class TestBaseStoreFrn:
    def test_frn_returns_expected_identifier(self):
        store = BaseStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.frn == f"store:platform={Platform.LOCAL}:storesystem={StoreSystem.FILE}:name=my_store"


class TestBaseStoreExport:
    def test_export_identity_is_none_when_not_set(self):
        store = BaseStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.export()["identity"] is None

    def test_export_identity_is_none_when_identity_is_plain_string(self):
        store = BaseStore(
            name="my_store",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            identity="some_identity_name",
        )
        assert store.export()["identity"] is None

    def test_export_includes_identity_name_when_identity_is_base_identity_instance(self):
        _identity = LocalIdentity(name="my_identity")
        store = BaseStore(
            name="my_store",
            storesystem=StoreSystem.FILE,
            platform=Platform.LOCAL,
            identity=_identity,
        )
        assert store.export()["identity"] == "my_identity"

    def test_describe_returns_valid_json_matching_export(self):
        store = BaseStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert json.loads(store.describe()) == store.export()


class TestBaseStoreFromSetting:
    def test_from_setting_is_a_placeholder_returning_none(self):
        # BaseStore.from_setting is meant to be overridden by subclasses;
        # on the base class itself it is a no-op stub.
        setting = FileStoreSetting(name="my_store")
        assert BaseStore.from_setting(setting) is None
