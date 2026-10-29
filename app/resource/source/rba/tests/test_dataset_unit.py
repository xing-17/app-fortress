from __future__ import annotations

import polars as pl
import pytest

from app.resource.source.rba.dataset import RBADataset


@pytest.fixture
def dataset(source):
    return source.dataset("cpi_month")


@pytest.fixture
def frame():
    return pl.DataFrame({"date": ["2024-01-31", "2024-02-29"], "value": [1.0, 2.0]})


class TestExtract:
    def test_returns_fetched_frame(self, dataset, frame, monkeypatch):
        monkeypatch.setattr(RBADataset, "_request", lambda self: frame)
        assert dataset.extract().equals(frame)

    def test_retries_until_request_succeeds(self, dataset, frame, monkeypatch):
        _calls: list[int] = []

        def _flaky(self):
            _calls.append(1)
            if len(_calls) < 2:
                raise ConnectionError("boom")
            return frame

        monkeypatch.setattr(RBADataset, "_request", _flaky)
        assert dataset.extract().height == 2
        assert len(_calls) == 2


class TestTransform:
    def test_adds_snapshotdate(self, dataset, frame):
        assert "snapshotdate" in dataset.transform(frame).columns

    def test_empty_frame_is_returned_as_is(self, dataset):
        assert dataset.transform(pl.DataFrame()).is_empty()


class TestWrite:
    def test_empty_frame_writes_nothing(self, dataset):
        assert dataset.write(pl.DataFrame()) == []

    def test_missing_partition_column_raises(self, dataset, frame):
        with pytest.raises(ValueError, match="partition columns"):
            dataset.write(frame)

    def test_writes_one_file_per_partition(self, dataset, frame):
        _files = dataset.write(dataset.transform(frame))
        assert len(_files) == 1
        assert _files[0].path.exists()
