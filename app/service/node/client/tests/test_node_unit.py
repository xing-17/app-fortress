from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from app.service.node.client.node import NodeClient
from app.service.node.dra import DRABusyError, DRADataResult, DRAQueryError, DRARejectedError
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
)

from .conftest import write_assetfile


class TestNodeClientIsAbstract:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            NodeClient()


class TestContract:
    """Every implementation answers the same, so these run on the local and the http client."""

    def test_is_a_node_client(self, client):
        assert isinstance(client, NodeClient)

    def test_context_manager_returns_the_client(self, client):
        with client as _inner:
            assert _inner is client

    def test_list_sources(self, client):
        _res = client.list_sources()
        assert [s["name"] for s in _res] == ["src"]
        assert sorted(_res[0]["datasets"]) == ["alpha", "beta"]

    def test_get_source(self, client):
        assert client.get_source("src")["name"] == "src"

    def test_get_unknown_source_raises(self, client):
        with pytest.raises(NodeSourceNotFoundError):
            client.get_source("nope")

    def test_list_datasets_of_all_and_one_source(self, client):
        assert sorted(d["dataset"] for d in client.list_datasets()) == ["src.alpha", "src.beta"]
        assert sorted(d["name"] for d in client.list_datasets("src")) == ["alpha", "beta"]

    def test_list_datasets_of_unknown_source_raises(self, client):
        with pytest.raises(NodeSourceNotFoundError):
            client.list_datasets("nope")

    def test_get_dataset(self, client):
        _res = client.get_dataset("src", "beta")
        assert _res["dataset"] == "src.beta"
        assert _res["partitions"] == ["year"]

    def test_get_unknown_dataset_raises(self, client):
        with pytest.raises(NodeDatasetNotFoundError):
            client.get_dataset("src", "nope")

    def test_list_assetfiles(self, client, source):
        write_assetfile(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        write_assetfile(source, "beta", "b.parquet", pl.DataFrame({"a": [1]}), {"year": "2024"})
        _res = client.list_assetfiles("src", "beta")
        assert sorted(f["partitions"]["year"] for f in _res) == ["2023", "2024"]

    def test_list_assetfiles_of_unknown_dataset_raises(self, client):
        with pytest.raises(NodeDatasetNotFoundError):
            client.list_assetfiles("src", "nope")

    def test_list_assetfiles_window(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _modified = client.list_assetfiles("src", "alpha")[0]["modified_at"]
        assert len(client.list_assetfiles("src", "alpha", since=_modified - 10)) == 1
        assert len(client.list_assetfiles("src", "alpha", since=_modified + 10)) == 0
        assert len(client.list_assetfiles("src", "alpha", until=_modified - 10)) == 0

    def test_list_assetfiles_window_accepts_datetimes(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        _now = datetime.now(timezone.utc)
        assert len(client.list_assetfiles("src", "alpha", since=_now - timedelta(days=1))) == 1
        assert len(client.list_assetfiles("src", "alpha", since=_now + timedelta(days=1))) == 0

    def test_list_metadatas(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        write_assetfile(source, "alpha", "bare.parquet", pl.DataFrame({"a": [1]}), metadata=False)
        _by_name = {m["assetfile"]["name"]: m["metadata"] for m in client.list_metadatas("src", "alpha")}
        assert set(_by_name["a.parquet"]) == {"quality", "definition"}
        assert _by_name["bare.parquet"] is None

    def test_list_qualities(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = client.list_qualities("src", "alpha")
        assert _res[0]["quality"]["height"] == 3

    def test_list_definitions(self, client, source):
        write_assetfile(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2022"})
        write_assetfile(source, "beta", "b.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        write_assetfile(source, "beta", "c.parquet", pl.DataFrame({"a": [1], "b": [2]}), {"year": "2024"})
        _by_size = {len(g["columns"]): g for g in client.list_definitions("src", "beta")}
        assert sorted(p["year"] for p in _by_size[1]["partitions"]) == ["2022", "2023"]
        assert [p["year"] for p in _by_size[2]["partitions"]] == ["2024"]

    def test_query(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = client.query("SELECT max(a) AS top FROM src.alpha")
        assert isinstance(_res, DRADataResult)
        assert _res.columns == ["top"]
        assert _res.rows == [[3]]
        assert _res.truncated is False

    def test_sum_of_integers_is_a_number(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1, 2, 3]}))
        _res = client.query("SELECT sum(a) AS total FROM src.alpha")
        assert _res.rows == [[6]]
        assert type(_res.rows[0][0]) is int

    def test_query_with_partitions(self, client, source):
        write_assetfile(source, "beta", "a.parquet", pl.DataFrame({"a": [1]}), {"year": "2023"})
        write_assetfile(source, "beta", "b.parquet", pl.DataFrame({"a": [5]}), {"year": "2024"})
        _res = client.query("SELECT max(a) FROM src.beta WHERE year = '2024'")
        assert _res.rows == [[5]]

    def test_rejected_query_raises(self, client):
        with pytest.raises(DRARejectedError):
            client.query("DROP TABLE x")

    def test_failed_query_raises(self, client, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"a": [1]}))
        with pytest.raises(DRAQueryError):
            client.query("SELECT nope FROM src.alpha")

    def test_blank_query_raises(self, client):
        with pytest.raises((NodeBadRequestError, DRARejectedError)):
            client.query("   ")

    def test_busy_node_raises(self, client, service, monkeypatch):
        def _busy(caller, sql):
            raise DRABusyError("every session is busy")

        monkeypatch.setattr(service, "query", _busy)
        with pytest.raises(DRABusyError, match="every session is busy"):
            client.query("SELECT 1")

    def test_health(self, client):
        _res = client.health()
        assert _res["kind"] == "node"
        assert _res["is_running"] is True
