from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source.abs import ABSSource
from app.resource.source.abs.datasets.job_vacancies_quarter import JobVacanciesQuarterDataset
from app.setting._source import ABSSourceSetting
from app.setting._store import FileStoreSetting
from app.setting._vault import LocalVaultSetting


@pytest.fixture
def source(vault, store, log_stream):
    return ABSSource(name="abs", vault=vault, store=store, log_stream=log_stream)


class TestABSSource:
    def test_frn_includes_provider_and_name(self, source):
        assert source.frn == f"source:provider={SourceProvider.ABS}:name=abs"

    def test_non_positive_timeout_is_rejected(self, vault, store):
        with pytest.raises(ValidationError):
            ABSSource(name="abs", timeout_seconds=0, vault=vault, store=store)

    def test_unknown_dataset_raises(self, source):
        with pytest.raises(ValueError, match="not found"):
            source.dataset("nope")

    def test_dataset_is_bound_to_source_resources(self, source):
        _dataset = source.dataset("job_vacancies_quarter")
        assert isinstance(_dataset, JobVacanciesQuarterDataset)
        assert _dataset.asset.path == source.vault.path / "job_vacancies_quarter"
        assert _dataset.database.path == source.store.path / "job_vacancies_quarter"
        assert _dataset.log_stream is source.log_stream
        assert _dataset.timeout_seconds == source.timeout_seconds

    def test_datasets_share_the_source_client(self, source):
        assert source.dataset("job_vacancies_quarter").client is source._client

    def test_dataset_metadata(self):
        assert JobVacanciesQuarterDataset.dataflow_id == "JV"
        assert JobVacanciesQuarterDataset.frequency == FrequencyOption.QUARTER

    def test_export_does_not_include_client(self, source):
        assert "client" not in source.dataset("job_vacancies_quarter").export()

    def test_from_setting_builds_source(self, tmp_path):
        _setting = ABSSourceSetting(
            name="abs",
            timeout_seconds=30,
            vault=LocalVaultSetting(name="v", path=str(tmp_path / "vault")),
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        _source = ABSSource.from_setting(_setting)
        assert _source.name == "abs"
        assert _source.timeout_seconds == 30
        assert "job_vacancies_quarter" in _source.list_dataset_names()
