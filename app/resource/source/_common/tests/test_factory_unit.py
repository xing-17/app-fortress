from __future__ import annotations

import pytest

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source._common._factory import SourceFactory
from app.resource.source._common._source import BaseSource
from app.resource.source.tushare.source import TushareSource
from app.setting._source import (
    ABSSourceSetting,
    TushareSourceSetting,
)


class TestSourceFactoryGet:
    def test_get_tushare_returns_tushare_source_class(self):
        assert SourceFactory.get(SourceProvider.TUSHARE) is TushareSource

    def test_get_accepts_plain_string_provider(self):
        assert SourceFactory.get("tushare") is TushareSource

    def test_get_returned_class_is_subclass_of_base_source(self):
        assert issubclass(SourceFactory.get(SourceProvider.TUSHARE), BaseSource)

    def test_get_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="No source registered"):
            SourceFactory.get("not_a_provider")

    def test_get_unimplemented_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="No source registered"):
            SourceFactory.get(SourceProvider.ABS)


class TestSourceFactoryRegistryValidation:
    def test_get_raises_type_error_when_target_is_not_a_class(self, monkeypatch):
        monkeypatch.setitem(SourceFactory._registry, "not_a_class", "os:getcwd")
        with pytest.raises(TypeError, match="Expecting class"):
            SourceFactory.get("not_a_class")

    def test_get_raises_type_error_when_target_is_not_base_source_subclass(self, monkeypatch):
        monkeypatch.setitem(
            SourceFactory._registry,
            "not_base_source",
            "app.resource.source._common._factory:SourceFactory",
        )
        with pytest.raises(TypeError, match="Expecting subclass of BaseSource"):
            SourceFactory.get("not_base_source")

    def test_registered_targets_all_resolve_to_base_source_subclasses(self):
        for _provider in SourceFactory._registry:
            assert issubclass(SourceFactory.get(_provider), BaseSource)


class TestSourceFactoryLoad:
    def test_load_returns_tushare_source_instance(self, vault, store, monkeypatch):
        monkeypatch.setattr("app.resource._global.vaults.GlobalVaults.vaults", {"v": vault})
        monkeypatch.setattr("app.resource._global.stores.GlobalStores.stores", {"s": store})
        setting = TushareSourceSetting(
            name="prod_tushare",
            key="token",
            vault="v",
            store="s",
            tags={"env": "prod"},
            session_ttl_hours=2,
        )
        source = SourceFactory.load(setting)
        assert isinstance(source, TushareSource)
        assert source.name == "prod_tushare"
        assert source.key == "token"
        assert source.ttl_hours == 2
        assert source.vault is vault
        assert source.store is store
        assert source.tags["env"] == "prod"

    def test_load_unimplemented_provider_raises_value_error(self):
        setting = ABSSourceSetting(name="abs", vault="v", store="s")
        with pytest.raises(ValueError, match="No source registered"):
            SourceFactory.load(setting)
