from __future__ import annotations

import io

import pandas as pd
import polars as pl
import pytest
from pydantic import ValidationError

from app.internal.constant.sourceprovider import SourceProvider
from app.resource.source.tushare import TushareSource
from app.resource.source.tushare.datasets.tradedates import TradedateDataset
from app.setting._source import TushareSourceSetting
from app.setting._store import FileStoreSetting
from app.setting._vault import LocalVaultSetting


@pytest.fixture
def source(vault, store, log_stream):
    return TushareSource(name="ts", key="k", vault=vault, store=store, log_stream=log_stream)


class TestTushareSource:
    def test_frn_includes_provider_and_name(self, source):
        assert source.frn == f"source:provider={SourceProvider.TUSHARE}:name=ts"

    def test_discovers_tradedates_dataset(self, source):
        assert source.list_dataset_names() == ["tradedates"]

    def test_empty_key_is_rejected(self, vault, store):
        with pytest.raises(ValidationError):
            TushareSource(name="ts", key="", vault=vault, store=store)

    def test_unknown_dataset_raises(self, source):
        with pytest.raises(ValueError, match="not found"):
            source.dataset("nope")

    def test_dataset_is_bound_to_source_resources(self, source):
        _dataset = source.dataset("tradedates")
        assert isinstance(_dataset, TradedateDataset)
        assert _dataset.asset.path == source.vault.path / "tradedates"
        assert _dataset.database.path == source.store.path / "tradedates"
        assert _dataset.log_stream is source.log_stream

    def test_from_setting_builds_source(self, tmp_path):
        _setting = TushareSourceSetting(
            name="ts",
            key="k",
            vault=LocalVaultSetting(name="v", path=str(tmp_path / "vault")),
            store=FileStoreSetting(name="s", path=str(tmp_path / "store")),
        )
        _source = TushareSource.from_setting(_setting)
        assert _source.name == "ts"
        assert _source.key == "k"
        assert _source.list_dataset_names() == ["tradedates"]


class TestTradedatesRun:
    def test_run_transforms_and_writes_by_snapshotdate(self, source, api):
        api.tradecal = pd.DataFrame(
            {
                "exchange": ["SSE", "SSE"],
                "cal_date": ["20240101", "20240102"],
                "is_open": [0, 1],
                "pretrade_date": ["20231229", "20231229"],
            }
        )
        _files = source.dataset("tradedates").run()
        assert len(_files) == 1
        _df = pl.read_parquet(io.BytesIO(_files[0].read_bytes()))
        assert _df.height == 2
        assert _df.schema["cal_date"] == pl.Date
        assert _df.schema["pretrade_date"] == pl.Date
        assert _df.schema["is_open"] == pl.Boolean
        assert _df["is_open"].to_list() == [False, True]
        assert "snapshotdate" in _df.columns

    def test_run_with_empty_tushare_result_writes_nothing(self, source, api):
        assert source.dataset("tradedates").run() == []
