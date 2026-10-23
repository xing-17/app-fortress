from __future__ import annotations

from datetime import datetime
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from app.internal.util.clock import IClock
from app.service._common.auth import Principal, TokenAuth
from app.service._common.http import BearerAuthMiddleware, JsonResponse
from app.service.node.dra import (
    DRABusyError,
    DRAError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
)
from app.service.node.service.service import NodeService

_MAX_BODY_BYTES = 1_000_000

# Exceptions the service raises on purpose, with the status the caller sees
_STATUS: dict[type[Exception], int] = {
    NodeSourceNotFoundError: 404,
    NodeDatasetNotFoundError: 404,
    DRARejectedError: 400,
    DRAQueryError: 400,
    DRAQueryTimeoutError: 408,
    DRABusyError: 503,
    NodeBadRequestError: 400,
}


class NodeHttp:
    """
    HTTP face of `NodeService`, a thin mapping with no logic of its own

    Every route except `GET /health` needs a bearer token. Catalog routes are plain `def`
    endpoints so Starlette runs them in its thread pool; `POST /internal/query` has to read the
    body and hands the blocking call to the pool itself.

    Routes:
    ----------
        GET  /health
        GET  /internal/sources
        GET  /internal/sources/{source}
        GET  /internal/datasets[?source=]
        GET  /internal/datasets/{source}/{dataset}
        GET  /internal/datasets/{source}/{dataset}/assetfiles[?since=&until=]
        GET  /internal/datasets/{source}/{dataset}/metadatas[?since=&until=]
        GET  /internal/datasets/{source}/{dataset}/qualities[?since=&until=]
        GET  /internal/datasets/{source}/{dataset}/definitions[?since=&until=]
        GET  /internal/machine/snapshots[?hours=]
        POST /internal/query            body {"sql": "SELECT ..."}

    `since` and `until` are epoch seconds (`modified_at` of an assetfile is one) or an ISO 8601
    datetime, a datetime without an offset is read as UTC. `hours` is a number above 0, the
    machine snapshots of that many past hours, all of them when absent.

    Errors:
    ----------
        401: missing or invalid token, same body for every cause
        400: malformed request, DRARejectedError, DRAQueryError
        404: unknown source or dataset
        408: DRAQueryTimeoutError
        503: DRABusyError, every session is running a query
        500: anything else, the body carries no detail

    Args:
    ----------
        service (NodeService):
            Running node service
        auth (TokenAuth):
            Token verifier

    Methods:
    ----------
        build() -> Starlette:
            The ASGI application

    """

    def __init__(
        self,
        service: NodeService,
        auth: TokenAuth,
    ) -> None:
        self._service = service
        self._auth = auth

    def build(self) -> Starlette:
        _prefix = "/internal"
        _dataset = f"{_prefix}/datasets/{{source}}/{{dataset}}"
        _routes = [
            Route("/health", self._health, methods=["GET"]),
            Route(f"{_prefix}/sources", self._list_sources, methods=["GET"]),
            Route(f"{_prefix}/sources/{{source}}", self._get_source, methods=["GET"]),
            Route(f"{_prefix}/datasets", self._list_datasets, methods=["GET"]),
            Route(_dataset, self._get_dataset, methods=["GET"]),
            Route(f"{_dataset}/assetfiles", self._list_assetfiles, methods=["GET"]),
            Route(f"{_dataset}/metadatas", self._list_metadatas, methods=["GET"]),
            Route(f"{_dataset}/qualities", self._list_qualities, methods=["GET"]),
            Route(f"{_dataset}/definitions", self._list_definitions, methods=["GET"]),
            Route(f"{_prefix}/machine/snapshots", self._list_machine_snapshots, methods=["GET"]),
            Route(f"{_prefix}/query", self._query, methods=["POST"]),
        ]
        _handlers: dict[Any, Any] = {_exc: self._handle_known_error for _exc in _STATUS}
        _handlers[DRAError] = self._handle_unexpected_error
        _handlers[Exception] = self._handle_unexpected_error
        _middleware = [
            Middleware(
                BearerAuthMiddleware,
                auth=self._auth,
                log=self._service.log,
            ),
        ]
        return Starlette(
            routes=_routes,
            middleware=_middleware,
            exception_handlers=_handlers,
        )

    # --------------------------------------------------
    # Errors
    # --------------------------------------------------

    def _handle_known_error(
        self,
        request: Request,
        exc: Exception,
    ) -> Response:
        _status: int = 500
        for _type in type(exc).__mro__:
            if _type in _STATUS:
                _status = _STATUS[_type]
                break

        return JsonResponse(
            {
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status_code=_status,
        )

    def _handle_unexpected_error(
        self,
        request: Request,
        exc: Exception,
    ) -> Response:
        # The service does not log what is not a DRAError in `query`, so it is logged here
        self._service.log.error(
            f"unhandled {type(exc).__name__}: {request.method} {request.url.path}",
            metadata={
                "caller": self._caller(request),
                "error": type(exc).__name__,
            },
        )
        return JsonResponse(
            {"error": "internal error"},
            status_code=500,
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _caller(request: Request) -> str:
        _principal: Principal | None = request.scope.get("state", {}).get("principal")
        return _principal.name if _principal is not None else "-"

    @staticmethod
    def _time(
        request: Request,
        name: str,
    ) -> datetime | float | None:
        _raw: str | None = request.query_params.get(name)
        if not _raw:
            return None
        try:
            return float(_raw)
        except ValueError:
            pass
        try:
            return IClock.from_iso(_raw)
        except ValueError:
            raise NodeBadRequestError(f"'{name}' must be epoch seconds or an ISO 8601 datetime") from None

    def _window(
        self,
        request: Request,
    ) -> dict[str, datetime | float | None]:
        return {
            "since": self._time(request, "since"),
            "until": self._time(request, "until"),
        }

    # --------------------------------------------------
    # Endpoints
    # --------------------------------------------------

    def _health(self, request: Request) -> Response:
        _res: dict = self._service.health()
        _status: int = 200 if self._service.is_running else 503
        return JsonResponse(_res, status_code=_status)

    def _list_sources(self, request: Request) -> Response:
        _res: list[dict[str, Any]] = self._service.list_sources()
        return JsonResponse(_res)

    def _get_source(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _res: dict = self._service.get_source(_source)
        return JsonResponse(_res)

    def _list_datasets(self, request: Request) -> Response:
        _source: str | None = request.query_params.get("source")
        _res: list[dict[str, Any]] = self._service.list_datasets(_source)
        return JsonResponse(_res)

    def _get_dataset(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _res: dict = self._service.get_dataset(_source, _dataset)
        return JsonResponse(_res)

    def _list_assetfiles(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _res = self._service.list_assetfiles(
            _source,
            _dataset,
            **self._window(request),
        )
        return JsonResponse(_res)

    def _list_metadatas(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _res = self._service.list_metadatas(
            source=_source,
            dataset=_dataset,
            **self._window(request),
        )
        return JsonResponse(_res)

    def _list_qualities(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _res = self._service.list_qualities(
            source=_source,
            dataset=_dataset,
            **self._window(request),
        )
        return JsonResponse(_res)

    def _list_definitions(self, request: Request) -> Response:
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _res = self._service.list_definitions(
            source=_source,
            dataset=_dataset,
            **self._window(request),
        )
        return JsonResponse(_res)

    def _list_machine_snapshots(self, request: Request) -> Response:
        _raw: str | None = request.query_params.get("hours")
        _hours: float | None = None
        if _raw:
            try:
                _hours = float(_raw)
            except ValueError:
                raise NodeBadRequestError("'hours' must be a number") from None
        _res = self._service.list_machine_snapshots(_hours)
        return JsonResponse(_res)

    async def _query(self, request: Request) -> Response:
        _length: str | None = request.headers.get("content-length")
        if _length is not None and _length.isdigit() and int(_length) > _MAX_BODY_BYTES:
            return JsonResponse({"error": "request too large"}, status_code=413)

        _body: bytes = await request.body()
        if len(_body) > _MAX_BODY_BYTES:
            return JsonResponse({"error": "request too large"}, status_code=413)

        try:
            _payload = await request.json()
        except ValueError:
            raise NodeBadRequestError("body must be JSON") from None

        _sql = _payload.get("sql") if isinstance(_payload, dict) else None
        if not isinstance(_sql, str) or not _sql.strip():
            raise NodeBadRequestError('body must be {"sql": "<one SELECT statement>"}')

        _principal: Principal = request.state.principal
        _res = await run_in_threadpool(self._service.query, _principal, _sql)
        return JsonResponse(_res)


def create_app(
    service: NodeService,
    auth: TokenAuth,
) -> Starlette:
    return NodeHttp(service, auth).build()


def serve(
    service: NodeService,
    auth: TokenAuth,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """
    Start the service, serve until interrupted, stop the service

    Host and port default to the node setting.

    """
    _setting = service.setting
    _app: Starlette = create_app(service, auth)
    service.start()
    try:
        uvicorn.run(
            _app,
            host=host or _setting.host,
            port=port or _setting.port,
            log_level="info",
        )
    finally:
        service.stop()
