from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from app.internal.util.clock import IClock
from app.internal.util.timezone import ITimezone
from app.resource.source.rba import RBASource
from app.resource.source.rba.dataset import RBADataset


@pytest.fixture
def dataset(source):
    return source.dataset("g4_cpi_month")


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

    def test_snapshotdate_follows_the_source_timezone(self, vault, store, log_stream, frame, monkeypatch):
        # 23:55 UTC on the 10th is already the 11th in Sydney
        _now = datetime(2026, 11, 10, 23, 55, tzinfo=ZoneInfo("UTC"))
        monkeypatch.setattr(
            IClock, "current", staticmethod(lambda timezone=None: _now.astimezone(ITimezone.resolve(timezone)))
        )
        _utc = RBASource(name="rba", vault=vault, store=store, log_stream=log_stream)
        _syd = RBASource(name="rba", vault=vault, store=store, log_stream=log_stream, timezone="Australia/Sydney")
        assert _utc.dataset("g4_cpi_month").transform(frame)["snapshotdate"].unique().to_list() == ["2026-11-10"]
        assert _syd.dataset("g4_cpi_month").transform(frame)["snapshotdate"].unique().to_list() == ["2026-11-11"]

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
