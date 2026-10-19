from __future__ import annotations

import pytest

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source.nswvg import NSWVGSource
from app.resource.source.nswvg.datasets.psi_week import WeekPSIDataset
from app.resource.source.nswvg.datasets.psi_year import YearPSIDataset
from app.setting._source import NSWVGSourceSetting
from app.setting._store import FileStoreSetting
from app.setting._vault import LocalVaultSetting


@pytest.fixture
def source(vault, store, log_stream, provision_root):
    return NSWVGSource(
        name="nsw",
        provision_path=provision_root,
        vault=vault,
        store=store,
        log_stream=log_stream,
    )


class TestNSWVGSource:
    def test_frn_includes_provider_and_name(self, source):
        assert source.frn == f"source:provider={SourceProvider.NSWVG}:name=nsw"

    def test_discovers_week_and_year_datasets(self, source):
        assert sorted(source.list_dataset_names()) == ["psi_week", "psi_year"]

    def test_unknown_dataset_raises(self, source):
        with pytest.raises(ValueError, match="not found"):
            source.dataset("nope")

    def test_dataset_is_bound_to_source_resources(self, source):
        _dataset = source.dataset("psi_week")
        assert isinstance(_dataset, WeekPSIDataset)
        assert _dataset.asset.path == source.vault.path / "psi_week"
        assert _dataset.database.path == source.store.path / "psi_week"
        assert _dataset.provision_path == source.provision_path / "psi_week"
        assert _dataset.log_stream is source.log_stream

    def test_each_dataset_has_its_own_provision_directory(self, source):
        _week = source.dataset("psi_week")
        _year = source.dataset("psi_year")
        assert isinstance(_year, YearPSIDataset)
        assert _week.provision_path != _year.provision_path

    def test_list_datasets_builds_all(self, source):
        assert sorted(_d.name for _d in source.list_datasets()) == ["psi_week", "psi_year"]

    def test_default_provision_path_is_derived_from_name(self, vault, store, log_stream):
        _source = NSWVGSource(name="nsw", vault=vault, store=store, log_stream=log_stream)
        assert _source.provision_path.name == "nsw"

    def test_from_setting_builds_source(self, tmp_path):
        _setting = NSWVGSourceSetting(
            name="nsw",
            provision_path=str(tmp_path / "prov"),
            vault=LocalVaultSetting(name="v", path=str(tmp_path / "vault")),
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        _source = NSWVGSource.from_setting(_setting)
        assert _source.name == "nsw"
        assert _source.provision_path == (tmp_path / "prov").resolve()
        assert sorted(_source.list_dataset_names()) == ["psi_week", "psi_year"]
