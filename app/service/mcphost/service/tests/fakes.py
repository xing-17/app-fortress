from __future__ import annotations

from typing import Any

from app.service.node.client.node import NodeClient
from app.service.node.dra import DRADataResult
from app.service.node.service.errors import NodeDatasetNotFoundError, NodeSourceNotFoundError


class FakeNodeClient(NodeClient):
    """Canned answers; set `raises` to make every call fail with that error."""

    def __init__(self) -> None:
        self.raises: Exception | None = None
        self.closed = False
        self.calls: list[tuple[str, tuple]] = []
        self.callers: list[str | None] = []
        self.sources: list[dict[str, Any]] = [{"name": "src"}]
        self.datasets: list[dict[str, Any]] = [
            {
                "source": "src",
                "dataset": "src.alpha",
                "name": "alpha",
                "description": "Alpha dataset",
                "frequency": "daily",
                "partitions": ["date"],
                "filekind": "parquet",
                "provider": "fake",
            },
        ]
        self.definitions: list[dict[str, Any]] = []
        self.qualities: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []
        self.result = DRADataResult(columns=["a"], types=["BIGINT"], rows=[[1]])
        self.node_health: dict[str, Any] = {"state": "running", "is_running": True}
        self.snapshots: list[dict[str, Any]] = []

    def _call(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))
        if self.raises is not None:
            raise self.raises

    def list_sources(self):
        self._call("list_sources")
        return self.sources

    def get_source(self, source):
        self._call("get_source", source)
        return self.sources[0]

    def list_datasets(self, source=None):
        self._call("list_datasets", source)
        if source is None:
            return self.datasets
        _items = [d for d in self.datasets if d["source"] == source]
        if not _items:
            raise NodeSourceNotFoundError(f"Source '{source}' not found on this node")
        return _items

    def get_dataset(self, source, dataset):
        self._call("get_dataset", source, dataset)
        for _d in self.datasets:
            if _d["dataset"] == f"{source}.{dataset}":
                return _d
        raise NodeDatasetNotFoundError(f"Dataset '{source}.{dataset}' not found on this node")

    def list_assetfiles(self, source, dataset, since=None, until=None):
        self._call("list_assetfiles", source, dataset)
        return []

    def list_metadatas(self, source, dataset, since=None, until=None):
        self._call("list_metadatas", source, dataset)
        return []

    def list_qualities(self, source, dataset, since=None, until=None):
        self._call("list_qualities", source, dataset)
        return list(self.qualities)

    def list_definitions(self, source, dataset, since=None, until=None):
        self._call("list_definitions", source, dataset)
        return self.definitions

    def list_runs(self, source, dataset, status=None, limit=None):
        self._call("list_runs", source, dataset, status, limit)
        return list(self.runs)

    def query(self, sql, caller=None):
        self._call("query", sql)
        self.callers.append(caller)
        return self.result

    def health(self):
        self._call("health")
        return self.node_health

    def list_machine_snapshots(self, hours=None):
        self._call("list_machine_snapshots", hours)
        return list(self.snapshots)

    def close(self):
        self.closed = True
