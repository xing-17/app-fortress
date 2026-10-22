from __future__ import annotations

import pytest

from app.internal.constant.sourceprovider import SourceProvider
from app.internal.logstream import LogStream
from app.resource.source._common._source import BaseSource
from app.resource.source._common.tests.fakes.base import FakeAbstractSource, FakeSource
from app.resource.source._common.tests.fakes.ok.alpha import AlphaDataset
from app.resource.source._common.tests.fakes.ok.beta import BetaDataset


class TestSourceInit:
    def test_resolves_vault_store_and_log_stream_instances(self, source, vault, store, log_stream):
        assert source.vault is vault
        assert source.store is store
        assert source.log_stream is log_stream

    def test_log_stream_defaults_to_stream_named_after_source(self, vault, store):
        _source = FakeSource(name="my_src", vault=vault, store=store)
        assert isinstance(_source.log_stream, LogStream)
        assert _source.log_stream.name == "my_src"

    def test_unknown_vault_name_raises(self, store, monkeypatch):
        monkeypatch.setattr(
            "app.resource._global.vaults.GlobalVaults.vaults",
            {},
        )
        with pytest.raises(ValueError, match="not found"):
            FakeSource(name="src", vault="nope", store=store)

    def test_named_vault_and_store_are_resolved_from_global(self, vault, store, monkeypatch):
        monkeypatch.setattr("app.resource._global.vaults.GlobalVaults.vaults", {"v": vault})
        monkeypatch.setattr("app.resource._global.stores.GlobalStores.stores", {"s": store})
        _source = FakeSource(name="src", vault="v", store="s")
        assert _source.vault is vault
        assert _source.store is store

    def test_description_defaults_to_none(self, source):
        assert source.description is None


class TestSourceIdentity:
    def test_frn_includes_provider_and_name(self, source):
        assert source.frn == f"source:provider={SourceProvider.TUSHARE}:name=src"

    def test_base_source_is_abstract(self):
        assert BaseSource.__abstractmethods__ == {"from_setting", "dataset"}


class TestDatasetDiscovery:
    def test_list_dataset_classes_finds_only_classes_defined_in_modules(self):
        _classes = FakeSource.list_dataset_classes()
        assert sorted(c.name for c in _classes) == ["alpha", "beta"]

    def test_imported_base_classes_are_not_discovered(self):
        _classes = FakeSource.list_dataset_classes()
        assert all(c.__module__.endswith((".alpha", ".beta")) for c in _classes)

    def test_abstract_dataset_class_raises_type_error(self, vault, store):
        with pytest.raises(TypeError, match="is abstract"):
            FakeAbstractSource(name="src", vault=vault, store=store)

    def test_list_dataset_names(self, source):
        assert sorted(source.list_dataset_names()) == ["alpha", "beta"]

    def test_get_dataset_class_by_name(self, source):
        assert source.get_dataset_class("alpha") is AlphaDataset
        assert source.get_dataset_class("beta") is BetaDataset

    def test_get_dataset_class_unknown_returns_none(self, source):
        assert source.get_dataset_class("nope") is None


class TestSourceDataset:
    def test_dataset_builds_instance_of_named_class(self, source):
        assert isinstance(source.dataset("alpha"), AlphaDataset)

    def test_dataset_unknown_name_raises(self, source):
        with pytest.raises(ValueError, match="not found"):
            source.dataset("nope")

    def test_dataset_inherits_source_tags(self, source):
        source.tags["env"] = "test"
        assert source.dataset("alpha").tags["env"] == "test"


class TestListDatasets:
    def test_returns_one_dataset_per_class(self, source):
        _datasets = source.list_datasets()
        assert sorted(d.name for d in _datasets) == ["alpha", "beta"]

    def test_instances_are_cached_between_calls(self, source):
        _first = source.list_datasets()
        _second = source.list_datasets()
        assert all(a is b for a, b in zip(_first, _second))

    def test_returned_list_is_a_copy(self, source):
        _first = source.list_datasets()
        _first.clear()
        assert len(source.list_datasets()) == 2


class TestShowAndExport:
    def test_show_logs_source_and_every_dataset(self, source, log_stream):
        source.show()
        _messages = [r.getMessage() for r in log_stream.collector.records]
        assert any("src" in m for m in _messages)
        assert any("alpha" in m for m in _messages)
        assert any("beta" in m for m in _messages)

    def test_export_contains_identity_and_child_exports(self, source):
        _res = source.export()
        assert _res["frn"] == source.frn
        assert _res["provider"] == "tushare"
        assert _res["type"] == "org"
        assert _res["board"] == str(source.board)
        assert _res["country"] == str(source.country)
        assert _res["name"] == "src"
        assert _res["vault"] == source.vault.export()
        assert _res["store"] == source.store.export()
