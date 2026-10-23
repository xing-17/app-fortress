from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from types import TracebackType
from typing import Any

from app.service.node.dra.result import DRADataResult


class NodeClient(ABC):
    """
    How a host service (mcphost, webhost) talks to one node, whatever the transport

    Methods mirror `NodeService`, so every implementation answers the same questions with the
    same shapes and raises the same errors (`NodeSourceNotFoundError`, `NodeDatasetNotFoundError`,
    `NodeBadRequestError`, `DRARejectedError`, `DRAQueryError`, `DRAQueryTimeoutError`,
    `DRABusyError`). A remote implementation also raises `NodeUnauthorizedError`,
    `NodeUnavailableError` and `NodeUnknownError`.

    `since` and `until` are epoch seconds (`modified_at` of an assetfile is one) or a datetime.

    Methods:
    ----------
        list_sources() -> list[dict]:
            Sources with their dataset names
        get_source(source) -> dict:
            One source with its dataset names
        list_datasets(source=None) -> list[dict]:
            Datasets of one source or all
        get_dataset(source, dataset) -> dict:
            One dataset
        list_assetfiles(source, dataset, since=None, until=None) -> list[dict]:
            Assetfiles of a dataset
        list_metadatas(source, dataset, since=None, until=None) -> list[dict]:
            Each assetfile with its metadata, None when it has none
        list_qualities(source, dataset, since=None, until=None) -> list[dict]:
            Each assetfile with its quality, None when it has no metadata
        list_definitions(source, dataset, since=None, until=None) -> list[dict]:
            Definitions grouped by fingerprint with the partitions that carry each of them
        query(sql, caller=None) -> DRADataResult:
            Run one SELECT on the node, as the identity this client holds, or as `caller` when
            that identity may delegate (the node names the principal `<identity>:<caller>`)
        list_machine_snapshots(hours=None) -> list[dict]:
            Snapshots of the node's host machine, oldest first, all of them or those of the last `hours`
        health() -> dict:
            Node state, does not need the node to be healthy
        close() -> None:
            Release what the client holds, a no-op by default

    """

    @abstractmethod
    def list_sources(self) -> list[dict[str, Any]]:
        """Sources with their dataset names."""

    @abstractmethod
    def get_source(
        self,
        source: str,
    ) -> dict[str, Any]:
        """One source with its dataset names."""

    @abstractmethod
    def list_datasets(
        self,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """Datasets of one source or all."""

    @abstractmethod
    def get_dataset(
        self,
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        """One dataset."""

    @abstractmethod
    def list_assetfiles(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        """Assetfiles of a dataset."""

    @abstractmethod
    def list_metadatas(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        """Each assetfile with its metadata, None when it has none."""

    @abstractmethod
    def list_qualities(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        """Each assetfile with its quality, None when it has no metadata."""

    @abstractmethod
    def list_definitions(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        """Definitions grouped by fingerprint with the partitions that carry each of them."""

    @abstractmethod
    def query(
        self,
        sql: str,
        caller: str | None = None,
    ) -> DRADataResult:
        """Run one SELECT on the node."""

    @abstractmethod
    def list_machine_snapshots(
        self,
        hours: float | None = None,
    ) -> list[dict[str, Any]]:
        """Snapshots of the node's host machine, oldest first."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Node state."""

    def close(self) -> None:
        return None

    def __enter__(self) -> NodeClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
