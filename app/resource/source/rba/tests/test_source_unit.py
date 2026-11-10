from __future__ import annotations

import pytest

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source.rba import RBADataset, RBASource
from app.resource.source.rba.datasets import G4CPIMonthDataset
from app.setting._source import RBASourceSetting
from app.setting._store import FileStoreSetting
from app.setting._vault import LocalVaultSetting


class TestRBASource:
    def test_frn_includes_provider_and_name(self, source):
        assert source.frn == f"source:provider={SourceProvider.RBA}:name=rba"

    def test_unknown_dataset_raises(self, source):
        with pytest.raises(ValueError, match="not found"):
            source.dataset("nope")

    def test_dataset_is_bound_to_source_resources(self, source):
        _dataset = source.dataset("g4_cpi_month")
        assert isinstance(_dataset, G4CPIMonthDataset)
        assert _dataset.asset.path == source.vault.path / "g4_cpi_month"
        assert _dataset.database.path == source.store.path / "g4_cpi_month"
        assert _dataset.log_stream is source.log_stream

    def test_from_setting_builds_source(self, tmp_path):
        _setting = RBASourceSetting(
            name="rba",
            vault=LocalVaultSetting(name="v", path=str(tmp_path / "vault")),
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        _source = RBASource.from_setting(_setting)
        assert _source.name == "rba"
        assert "g4_cpi_month" in _source.list_dataset_names()


class TestRBADatasets:
    def test_every_dataset_declares_a_table_no(self, source):
        for _name in source.list_dataset_names():
            _klass = source.get_dataset_class(_name)
            assert issubclass(_klass, RBADataset)
            assert _klass.table_no
