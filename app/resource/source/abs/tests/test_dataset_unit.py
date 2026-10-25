from __future__ import annotations

import io
from typing import ClassVar

import polars as pl
import pytest
import requests

from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset
from app.resource.source.abs.tests.conftest import JV_CSV, make_response


class DemoDataset(ABSDataset):
    name: ClassVar[str] = "demo"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    dataflow_id: ClassVar[str] = "JV"


class VersionedDataset(DemoDataset):
    name: ClassVar[str] = "versioned"
    version: ClassVar[str | None] = "1.0.0"
    key: ClassVar[str] = "M2..AUS.Q"


def _build(klass, client, vault, store, log_stream):
    return klass(
        client=client,
        timeout_seconds=7,
        asset=vault.asset(rel=klass.name, filekind=klass.filekind, partitions=klass.partitions),
        database=store.database(klass.name),
        log_stream=log_stream,
        tags={},
        _authorized=True,
    )


@pytest.fixture
def dataset(client, vault, store, log_stream):
    return _build(DemoDataset, client, vault, store, log_stream)


class TestExtract:
    def test_reads_csv_as_strings(self, dataset, client):
        client.replies = [make_response(200, JV_CSV)]
        _df = dataset.extract()
        assert _df.height == 3
        assert set(_df.schema.values()) == {pl.String}

    def test_requests_csv_with_params_and_timeout(self, dataset, client):
        client.replies = [make_response(200, JV_CSV)]
        dataset.extract({"startPeriod": "2024"})
        _call = client.calls[0]
        assert _call["url"] == "https://data.api.abs.gov.au/rest/data/JV/all"
        assert _call["params"] == {"startPeriod": "2024", "format": "csv"}
        assert _call["timeout"] == 7

    def test_url_with_agency_version_and_key(self, client, vault, store, log_stream):
        _ds = _build(VersionedDataset, client, vault, store, log_stream)
        client.replies = [make_response(200, JV_CSV)]
        _ds.extract()
        assert client.calls[0]["url"] == "https://data.api.abs.gov.au/rest/data/ABS,JV,1.0.0/M2..AUS.Q"

    def test_no_records_found_is_an_empty_frame(self, dataset, client):
        client.replies = [make_response(404, "NoRecordsFound")]
        assert dataset.extract().is_empty()
        assert len(client.calls) == 1

    def test_empty_body_is_an_empty_frame(self, dataset, client):
        client.replies = [make_response(200, "")]
        assert dataset.extract().is_empty()


class TestExtractErrors:
    def test_unknown_dataflow_is_raised_without_retry(self, dataset, client):
        client.replies = [make_response(404, "Could not find Dataflow and/or DSD related with this data request")]
        with pytest.raises(requests.HTTPError):
            dataset.extract()
        assert len(client.calls) == 1

    def test_bad_key_is_raised_without_retry(self, dataset, client):
        client.replies = [make_response(422, "Not enough key values in query, expecting 6 got 5")]
        with pytest.raises(requests.HTTPError):
            dataset.extract()
        assert len(client.calls) == 1

    def test_server_error_is_retried_then_succeeds(self, dataset, client):
        client.replies = [make_response(503, ""), make_response(503, ""), make_response(200, JV_CSV)]
        assert dataset.extract().height == 3
        assert len(client.calls) == 3

    def test_persistent_server_error_gives_up_after_five_retries(self, dataset, client):
        client.replies = [make_response(503, "")]
        with pytest.raises(requests.HTTPError):
            dataset.extract()
        assert len(client.calls) == 6  # first call + 5 retries

    def test_retry_template_is_not_consumed(self, dataset, client):
        client.replies = [make_response(503, ""), make_response(200, JV_CSV)]
        dataset.extract()
        assert DemoDataset.retry._attempt == 0


class TestTransform:
    def test_casts_obs_value_and_adds_snapshotdate(self, dataset, client):
        client.replies = [make_response(200, JV_CSV)]
        _df = dataset.transform(dataset.extract())
        assert _df.schema["OBS_VALUE"] == pl.Float64
        assert _df["OBS_VALUE"].to_list() == [1.0, 0.9, None]  # "n/a" -> null
        assert "snapshotdate" in _df.columns

    def test_empty_frame_stays_empty(self, dataset):
        assert dataset.transform(pl.DataFrame()).is_empty()


class TestRun:
    def test_run_writes_one_snapshotdate_partition(self, dataset, client):
        client.replies = [make_response(200, JV_CSV)]
        _files = dataset.run()
        assert len(_files) == 1
        _df = pl.read_parquet(io.BytesIO(_files[0].read_bytes()))
        assert _df.height == 3
        assert _files[0].partitions["snapshotdate"] == _df["snapshotdate"][0]

    def test_run_without_records_writes_nothing_and_completes(self, dataset, client):
        client.replies = [make_response(404, "NoRecordsFound")]
        assert dataset.run() == []
        assert [_r.status for _r in dataset.list_runs()] == [ComputeStatus.COMPLETED]

    def test_run_failure_is_recorded_and_raised(self, dataset, client):
        client.replies = [make_response(404, "Could not find Dataflow")]
        with pytest.raises(requests.HTTPError):
            dataset.run()
        assert [_r.status for _r in dataset.list_runs()] == [ComputeStatus.FAILED]
