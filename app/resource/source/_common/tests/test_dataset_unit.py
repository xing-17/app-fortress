from __future__ import annotations

import polars as pl
import pytest

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source._common.tests.fakes.ok.alpha import AlphaDataset


@pytest.fixture
def dataset(source):
    return source.dataset("alpha")


class TestDatasetIdentity:
    def test_frn_includes_provider_and_name(self, dataset):
        assert dataset.frn == f"source:provider={SourceProvider.TUSHARE}:dataset:name=alpha"

    def test_class_defaults(self):
        assert AlphaDataset.partitions == []
        assert AlphaDataset.description == ""
        assert AlphaDataset.frequency == FrequencyOption.DAY

    def test_dataset_is_bound_to_source_resources(self, dataset, source):
        assert dataset.log_stream is source.log_stream
        assert dataset.asset.path == source.vault.path / "alpha"
        assert dataset.asset.filekind == AssetFileKind.PARQUET
        assert dataset.database.path == source.store.path / "alpha"


class TestDatasetRun:
    def test_run_chains_extract_transform_write(self, dataset):
        _files = dataset.run()
        assert len(_files) == 1
        assert _files[0].read_bytes() == b"payload"

    def test_run_passes_params_to_extract(self, dataset, monkeypatch):
        _seen = {}

        def _extract(self, params=None):
            _seen["params"] = params
            return pl.DataFrame({"a": [1]})

        # Patch on the class: assigning to a governed pydantic instance re-runs the construction guard
        monkeypatch.setattr(type(dataset), "extract", _extract)
        dataset.run(params={"k": "v"})
        assert _seen["params"] == {"k": "v"}

    def test_run_logs_success_and_completion(self, dataset, log_stream):
        dataset.run()
        _messages = [r.getMessage() for r in log_stream.collector.records]
        assert any("run OK" in m for m in _messages)
        assert any("run completed" in m for m in _messages)

    def test_run_logs_and_reraises_on_failure(self, dataset, log_stream, monkeypatch):
        def _boom(self, params=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(type(dataset), "extract", _boom)
        with pytest.raises(RuntimeError, match="boom"):
            dataset.run()
        _messages = [r.getMessage() for r in log_stream.collector.records]
        assert any("run failed: boom" in m for m in _messages)
        assert not any("run completed" in m for m in _messages)


class TestDatasetRunRecords:
    def test_no_records_before_any_run(self, dataset):
        assert dataset.list_runs() == []

    def test_completed_run_is_recorded(self, dataset):
        _files = dataset.run(params={"k": "v"})
        _runs = dataset.list_runs()
        assert len(_runs) == 1
        assert _runs[0].status == ComputeStatus.COMPLETED
        assert _runs[0].provider == str(SourceProvider.TUSHARE)
        assert _runs[0].dataset == "alpha"
        assert _runs[0].params == {"k": "v"}
        assert _runs[0].assetfiles == [_files[0].uri]
        assert (_runs[0].height, _runs[0].width) == (3, 2)
        assert _runs[0].finished_at is not None

    def test_failed_run_is_recorded_and_reraised(self, dataset, monkeypatch):
        def _boom(self, params=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(type(dataset), "extract", _boom)
        with pytest.raises(RuntimeError, match="boom"):
            dataset.run()
        _runs = dataset.list_runs()
        assert len(_runs) == 1
        assert _runs[0].status == ComputeStatus.FAILED
        assert _runs[0].error == "boom"
        assert _runs[0].assetfiles == []

    def test_get_run_returns_the_record_of_the_id(self, dataset):
        dataset.run()
        _run = dataset.list_runs()[0]
        assert dataset.get_run(_run.id).export() == _run.export()

    def test_get_run_of_unknown_id_returns_none(self, dataset):
        assert dataset.get_run("run-missing") is None

    def test_runs_are_stored_in_the_run_table(self, dataset):
        dataset.run()
        assert dataset.get_run_table().path.parent == dataset.database.path
        assert dataset.get_run_table().path.stem == dataset._run_table_name

    def test_list_runs_is_newest_first(self, dataset):
        dataset.run()
        dataset.run()
        dataset.run()
        _started = [r.started_at for r in dataset.list_runs()]
        assert _started == sorted(_started, reverse=True)
        assert len(_started) == 3

    def test_list_runs_limit_keeps_the_newest(self, dataset):
        for _ in range(3):
            dataset.run()
        _all = dataset.list_runs()
        assert [r.id for r in dataset.list_runs(limit=2)] == [r.id for r in _all[:2]]

    def test_list_runs_filters_by_status(self, dataset, monkeypatch):
        dataset.run()

        def _boom(self, params=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(type(dataset), "extract", _boom)
        with pytest.raises(RuntimeError):
            dataset.run()
        assert len(dataset.list_runs()) == 2
        assert [r.status for r in dataset.list_runs(status=ComputeStatus.FAILED)] == [ComputeStatus.FAILED]
        assert [r.status for r in dataset.list_runs(status=ComputeStatus.COMPLETED)] == [ComputeStatus.COMPLETED]

    def test_run_records_are_capped(self, dataset, monkeypatch):
        monkeypatch.setattr(type(dataset), "_max_run_records", 2)
        for _ in range(3):
            dataset.run()
        assert len(dataset.list_runs()) == 2


class TestDatasetAssetfiles:
    def test_write_and_read_assetfile_round_trip(self, dataset):
        _file = dataset.asset.assetfile("data.parquet")
        dataset.write_assetfile(_file, b"hello")
        assert dataset.read_assetfile(_file) == b"hello"

    def test_list_assetfiles_returns_written_files(self, dataset):
        dataset.run()
        _files = dataset.list_assetfiles()
        assert [f.name for f in _files] == ["data.parquet"]

    def test_list_assetfiles_is_empty_before_any_write(self, dataset):
        assert dataset.list_assetfiles() == []


class TestDatasetMetadata:
    def test_metadata_table_lives_in_dataset_database(self, dataset):
        _table = dataset.get_metadata_table("data.parquet")
        assert _table.path.parent == dataset.database.path

    def test_write_then_read_metadata_round_trip(self, dataset):
        _file = dataset.asset.assetfile("data.parquet")
        _metadata = dataset.get_metadata(pl.DataFrame({"a": [1, 2, 3]}))
        dataset.write_metadata(_file, _metadata)
        _loaded = dataset.read_metadata(_file)
        assert _loaded.export() == _metadata.export()

    def test_read_metadata_of_unknown_assetfile_return_none(self, dataset):
        _file = dataset.asset.assetfile("missing.parquet")
        assert dataset.read_metadata(_file) is None

    def test_list_metadatas_reads_metadata_of_each_assetfile(self, dataset):
        _files = dataset.run()
        _metadata = dataset.get_metadata(pl.DataFrame({"a": [1]}))
        dataset.write_metadata(_files[0], _metadata)
        _result = dataset.list_metadatas()
        assert [m.export() for m in _result] == [_metadata.export()]


class TestDatasetExport:
    def test_export_contains_identity_fields(self, dataset):
        _res = dataset.export()
        assert _res["frn"] == dataset.frn
        assert _res["provider"] == "tushare"
        assert _res["name"] == "alpha"
        assert _res["frequency"] == "DAY"
        assert _res["filekind"] == "parquet"
        assert _res["partitions"] == []

    def test_export_embeds_asset_and_database_exports(self, dataset):
        _res = dataset.export()
        assert _res["asset"] == dataset.asset.export()
        assert _res["database"] == dataset.database.export()
        assert "log_stream" not in _res
