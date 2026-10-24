from __future__ import annotations

from datetime import datetime
from typing import Any

from app.service._common.auth import Principal
from app.service.node.client.node import NodeClient
from app.service.node.dra.result import DRADataResult
from app.service.node.service.service import NodeService


class LocalNodeClient(NodeClient):
    """
    `NodeClient` over a `NodeService` in the same process, no HTTP and no token

    The client does not own the service: the caller starts and stops it, `close` does nothing.
    Every query runs as `caller`, so they share one DRA session.

    Args:
    ----------
        service (NodeService):
            Running node service
        caller (Principal | None):
            Identity of the queries, defaults to the principal "local"

    """

    def __init__(
        self,
        service: NodeService,
        caller: Principal | None = None,
    ) -> None:
        self._service = service
        self._caller: Principal = self._resolve_caller(caller)

    def _resolve_caller(
        self,
        caller: Principal | None = None,
    ) -> Principal:
        if not caller:
            return Principal(name="local", description="Default local caller")
        else:
            return caller

    # --------------------------------------------------
    # Catalog: Dataset and Source Catalog API
    # --------------------------------------------------

    def list_sources(self) -> list[dict[str, Any]]:
        return self._service.list_sources()

    def get_source(
        self,
        source: str,
    ) -> dict[str, Any]:
        return self._service.get_source(source)

    def list_datasets(
        self,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_datasets(source)

    def get_dataset(
        self,
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        return self._service.get_dataset(
            source=source,
            dataset=dataset,
        )

    def list_assetfiles(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_assetfiles(
            source=source,
            dataset=dataset,
            since=since,
            until=until,
        )

    def list_metadatas(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_metadatas(
            source=source,
            dataset=dataset,
            since=since,
            until=until,
        )

    def list_qualities(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_qualities(
            source=source,
            dataset=dataset,
            since=since,
            until=until,
        )

    def list_definitions(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_definitions(
            source=source,
            dataset=dataset,
            since=since,
            until=until,
        )

    def list_runs(
        self,
        source: str,
        dataset: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_runs(
            source=source,
            dataset=dataset,
            status=status,
            limit=limit,
        )

    # --------------------------------------------------
    # DRA: Data Retrieval API
    # --------------------------------------------------

    def query(
        self,
        sql: str,
        caller: str | None = None,
    ) -> DRADataResult:
        _principal: Principal = self._caller
        if caller is not None:
            _principal = Principal(
                name=f"{_principal.name}:{caller}",
                description=_principal.description,
            )
        return self._service.query(_principal, sql)

    # --------------------------------------------------
    # MACHINE: State of the host machine
    # --------------------------------------------------

    def list_machine_snapshots(
        self,
        hours: float | None = None,
    ) -> list[dict[str, Any]]:
        return self._service.list_machine_snapshots(hours)

    # --------------------------------------------------
    # HEALTH: Check the health status of the node
    # --------------------------------------------------

    def health(self) -> dict[str, Any]:
        return self._service.health()
