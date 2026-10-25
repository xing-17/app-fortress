from __future__ import annotations

import json
import time
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, wait
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.internal.logstream import LogStream
from app.internal.util.timezone import ITimezone
from app.service._common.auth import AuthError, Principal, TokenAuth
from app.service._common.http import JsonResponse
from app.service.node.client.node import NodeClient
from app.service.node.dra import (
    DRABusyError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeBusyError,
    NodeDatasetNotFoundError,
    NodeRunNotFoundError,
    NodeSourceNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
    NodeUnknownError,
)
from app.service.webhost.service import machine, shape
from app.service.webhost.service.auth import (
    COOKIE_NAME,
    SESSION_TTL_SECONDS,
    SessionStore,
    safe_next,
)
from app.setting.service import NodeEndpointSetting

_ROOT = Path(__file__).parent
_PROBE_TIMEOUT_SECONDS = 6.0
_MACHINE_HOURS = 1.0
_RUN_LIMIT = 30
_LOG_LIMIT = 200
_MAX_LISTED = 300
_MAX_SQL_CHARS = 100_000
_MAX_FORM_BYTES = 4096
_TABS = ("partitions", "quality", "definitions", "runs")


class UnknownNodeError(LookupError):
    """The URL names a node this host does not serve"""


# Status the caller sees, the message of these is meant for the person
_STATUS: dict[type[Exception], int] = {
    UnknownNodeError: 404,
    NodeSourceNotFoundError: 404,
    NodeDatasetNotFoundError: 404,
    NodeRunNotFoundError: 404,
    NodeBadRequestError: 400,
    DRARejectedError: 400,
    DRAQueryError: 400,
    DRAQueryTimeoutError: 408,
    NodeBusyError: 503,
    DRABusyError: 503,
    NodeUnauthorizedError: 502,
    NodeUnavailableError: 502,
    NodeUnknownError: 502,
}


def _describe(error: Exception) -> str:
    return str(error) or type(error).__name__


class WebPages:
    """
    The routes of the web console, every answer comes from a `NodeClient`

    Pages are server-rendered, the few calls the page makes itself (run a dataset and poll it, read
    logs, query) answer JSON. Route handlers are plain `def`, so Starlette runs the blocking client
    in its thread pool.

    Args:
    ----------
        nodes (list[NodeEndpointSetting]):
            The nodes served, in the order shown
        clients (Mapping[str, NodeClient]):
            One client per node name
        auth (TokenAuth):
            Verifier of the tokens pasted into the login page
        sessions (SessionStore):
            Sessions opened by the login page
        log (LogStream):
            Audit log
        pool (ThreadPoolExecutor):
            Runs the per-node probes of the overview side by side
        display_timezone (str):
            IANA timezone every time on the pages is shown in

    Methods:
    ----------
        routes() -> list:
            The Starlette routes
        exception_handlers() -> dict:
            Error handlers, a page for a browser and JSON for a call

    """

    def __init__(
        self,
        nodes: list[NodeEndpointSetting],
        clients: Mapping[str, NodeClient],
        auth: TokenAuth,
        sessions: SessionStore,
        log: LogStream,
        pool: ThreadPoolExecutor,
        display_timezone: str,
    ) -> None:
        self._nodes: dict[str, NodeEndpointSetting] = {n.name: n for n in nodes}
        self._clients: dict[str, NodeClient] = dict(clients)
        self._auth = auth
        self._sessions = sessions
        self._log = log
        self._pool = pool
        self._zone: ZoneInfo = ITimezone.resolve(display_timezone)
        self._templates_path: Path = _ROOT / "templates"
        self._templates = Jinja2Templates(
            directory=str(self._templates_path),
        )
        _env = self._templates.env
        _env.filters.update(
            size=shape.human_size,
            mb=shape.human_mb,
            duration=shape.human_duration,
            local=partial(shape.local_text, zone=self._zone),
            brief=shape.brief,
            column=shape.column_label,
            num=shape.human_count,
        )
        _env.globals["spark"] = shape.sparkline

    # --------------------------------------------------
    # Wiring
    # --------------------------------------------------

    def routes(self) -> list:
        _dataset = "/n/{node}/d/{source}/{dataset}"
        return [
            Route("/", self.home, methods=["GET"]),
            Route("/login", self.login_page, methods=["GET"]),
            Route("/login", self.login, methods=["POST"]),
            Route("/logout", self.logout, methods=["POST"]),
            Route("/n/{node}", self.node_page, methods=["GET"]),
            Route("/n/{node}/machine", self.machine_page, methods=["GET"]),
            Route("/n/{node}/s/{source}/logs", self.source_logs, methods=["GET"]),
            Route(_dataset, self.dataset_page, methods=["GET"]),
            Route(f"{_dataset}/runs", self.submit_run, methods=["POST"]),
            Route(f"{_dataset}/runs/{{id}}", self.get_run, methods=["GET"]),
            Route("/n/{node}/query", self.query_page, methods=["GET"]),
            Route("/n/{node}/query", self.query, methods=["POST"]),
            Mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static"),
            Mount("/logo", StaticFiles(directory=str(_ROOT / "logo")), name="logo"),
        ]

    def exception_handlers(self) -> dict[Any, Any]:
        _handlers: dict[Any, Any] = {}
        for _exc in _STATUS:
            _handlers[_exc] = self._on_known_error
        _handlers[HTTPException] = self._on_http_error
        _handlers[Exception] = self._on_unexpected_error
        return _handlers

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _client(self, name: str) -> NodeClient:
        _client: NodeClient | None = self._clients.get(name)
        if _client is None:
            _msg: str = f"Node '{name}' is not served by this host"
            raise UnknownNodeError(_msg)
        return _client

    @staticmethod
    def _principal(request: Request) -> Principal:
        _res: Principal = request.scope["state"]["principal"]
        return _res

    def _render(
        self,
        request: Request,
        name: str,
        status: int = 200,
        **context: Any,
    ) -> Response:
        _state: dict = request.scope.get("state", {})
        _principal: Principal | None = _state.get("principal")
        _context: dict[str, Any] = {
            "user": _principal.name if _principal else None,
            "can_logout": _state.get("via") == "session",
            "node_names": list(self._nodes),
            "refresh": 0,
            "bare": False,
            "page": None,
            "node": None,
            "nav": [],
            "source": None,
            "dataset": None,
            **context,
        }
        return self._templates.TemplateResponse(
            request=request,
            name=name,
            context=_context,
            status_code=status,
        )

    @staticmethod
    async def _json_body(request: Request, limit: int) -> dict[str, Any]:
        _raw: bytes = await request.body()
        if len(_raw) > limit:
            raise NodeBadRequestError("request body is too large")
        if not _raw:
            return {}
        try:
            _body: Any = json.loads(_raw)
        except ValueError:
            raise NodeBadRequestError("request body is not JSON") from None
        if not isinstance(_body, dict):
            raise NodeBadRequestError("request body must be a JSON object")
        return _body

    @staticmethod
    def _nav(client: NodeClient) -> list[dict[str, Any]]:
        # The sidebar is a convenience
        # a node that cannot list shows the page without it
        try:
            _sources = []
            for _s in client.list_sources():
                _source = {
                    "name": _s["name"],
                    "datasets": list(_s.get("datasets", [])),
                }
                _sources.append(_source)
            return _sources
        except Exception:
            return []

    # --------------------------------------------------
    # Login
    # --------------------------------------------------

    def login_page(self, request: Request) -> Response:
        _next: str = safe_next(request.query_params.get("next"))
        return self._render(
            request,
            "login.html",
            bare=True,
            next=_next,
            error=None,
        )

    async def login(self, request: Request) -> Response:
        _raw: bytes = await request.body()
        _form: dict[str, list[str]] = {}
        if len(_raw) <= _MAX_FORM_BYTES:
            _form = parse_qs(_raw.decode("utf-8", "replace"))
        _token: str = _form.get("token", [""])[0].strip()
        _next: str = safe_next(_form.get("next", [""])[0])
        try:
            _principal: Principal = self._auth.verify(_token)
        except AuthError as e:
            self._log.warning(
                f"web login rejected, reason: {e.reason}",
                metadata={
                    "reason": e.reason,
                    "client": request.client.host if request.client else "-",
                },
            )
            return self._render(
                request,
                "login.html",
                status=401,
                bare=True,
                next=_next,
                error="Invalid token",
            )

        _sid: str = self._sessions.create(_principal)
        self._log.info(
            "web login",
            metadata={"user": _principal.name},
        )
        _response = RedirectResponse(_next, status_code=303)
        _response.set_cookie(
            COOKIE_NAME,
            _sid,
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            path="/",
        )
        return _response

    def logout(self, request: Request) -> Response:
        self._sessions.drop(request.cookies.get(COOKIE_NAME))
        _response = RedirectResponse("/login", status_code=303)
        _response.delete_cookie(COOKIE_NAME, path="/")
        return _response

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    def _blank_card(self, name: str) -> dict[str, Any]:
        return {
            "name": name,
            "endpoint": self._nodes[name].endpoint,
            "reachable": False,
            "running": False,
            "state": "unreachable",
            "error": None,
            "health": {},
            "sources": None,
            "datasets": None,
            "machine": None,
            "notes": [],
        }

    def _probe(self, name: str) -> dict[str, Any]:
        _card: dict[str, Any] = self._blank_card(name)
        _client: NodeClient = self._clients[name]
        try:
            _health: dict[str, Any] = _client.health()
        except Exception as e:
            _card["error"] = _describe(e)
            return _card

        _card["reachable"] = True
        _card["health"] = _health
        _card["state"] = str(_health.get("state", "unknown"))
        _card["running"] = bool(_health.get("is_running"))
        if not _card["running"]:
            return _card

        try:
            _sources: list[dict[str, Any]] = _client.list_sources()
            _card["sources"] = len(_sources)
            _card["datasets"] = sum(len(s.get("datasets", [])) for s in _sources)
        except Exception as e:
            _card["notes"].append(_describe(e))
        _card["machine"] = self._machine(
            _client,
            _MACHINE_HOURS,
            _card["notes"],
        )
        return _card

    @staticmethod
    def _machine(
        client: NodeClient,
        hours: float,
        notes: list[str],
    ) -> dict[str, Any] | None:
        try:
            _snaps: list[dict[str, Any]] = client.list_machine_snapshots(hours=hours)
        except Exception as e:
            notes.append(_describe(e))
            return None
        if not _snaps:
            return None
        _last: dict[str, Any] = _snaps[-1]
        _stamp = _last.get("timestamp")
        return {
            "last": _last,
            "cpu": shape.series(_snaps, "cpu_percent"),
            "mem": shape.series(_snaps, "mem_percent"),
            "age": time.time() - _stamp if isinstance(_stamp, (int, float)) else None,
        }

    def home(self, request: Request) -> Response:
        _futures: dict[str, Future] = {}
        for name in self._nodes:
            _futures[name] = self._pool.submit(self._probe, name)
        wait(list(_futures.values()), timeout=_PROBE_TIMEOUT_SECONDS)
        _cards: list[dict[str, Any]] = []
        for _name, _future in _futures.items():
            if _future.done() and _future.exception() is None:
                _cards.append(_future.result())
                continue
            _card: dict[str, Any] = self._blank_card(_name)
            _card["error"] = "no answer in time" if not _future.done() else "probe failed"
            _cards.append(_card)
        return self._render(request, "home.html", page="home", cards=_cards, refresh=30)

    # --------------------------------------------------
    # Sources and datasets
    # --------------------------------------------------

    def node_page(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _client: NodeClient = self._client(_node)
        _health: dict[str, Any] = _client.health()
        _running: bool = bool(_health.get("is_running"))

        _sources: list[dict[str, Any]] = []
        _navs: list[dict[str, Any]] = []
        if _running:
            _datasets: list[dict[str, Any]] = _client.list_datasets()
            _by_source: dict[str, list[dict[str, Any]]] = {}
            for _item in _datasets:
                _by_source.setdefault(_item["source"], []).append(_item)
            for _source in _client.list_sources():
                _sources.append(
                    {
                        **_source,
                        "facts": shape.facts(_source),
                        "items": _by_source.get(_source["name"], []),
                    }
                )
                _navs.append(
                    {
                        "name": _source["name"],
                        "datasets": list(_source.get("datasets", [])),
                    }
                )

        return self._render(
            request,
            "node.html",
            page="node",
            node=_node,
            nav=_navs,
            endpoint=self._nodes[_node].endpoint,
            health=_health,
            running=_running,
            sources=_sources,
            refresh=30,
        )

    def machine_page(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _client: NodeClient = self._client(_node)
        _health: dict[str, Any] = _client.health()
        _running: bool = bool(_health.get("is_running"))

        _hours: int = machine.DEFAULT_HOURS
        try:
            _asked: int = int(request.query_params.get("hours", ""))
        except ValueError:
            _asked = _hours
        if _asked in machine.HOURS:
            _hours = _asked

        _notes: list[str] = []
        _view: dict[str, Any] | None = None
        if _running:
            try:
                _snaps: list[dict[str, Any]] = _client.list_machine_snapshots(hours=_hours)
                _view = machine.machine_view(_snaps, self._zone)
            except Exception as e:
                _notes.append(_describe(e))

        return self._render(
            request,
            "machine.html",
            page="machine",
            node=_node,
            nav=self._nav(_client) if _running else [],
            endpoint=self._nodes[_node].endpoint,
            health=_health,
            running=_running,
            view=_view,
            hours=_hours,
            ranges=machine.HOURS,
            notes=_notes,
            refresh=30,
        )

    def source_logs(self, request: Request) -> Response:
        _client: NodeClient = self._client(request.path_params["node"])
        _limit: int = _LOG_LIMIT
        _raw: str | None = request.query_params.get("limit")
        if _raw is not None:
            try:
                _limit = int(_raw)
            except ValueError:
                raise NodeBadRequestError("'limit' must be an integer") from None
        _limit = max(1, min(_limit, 1000))
        _events: list[dict[str, Any]] = _client.list_logs(
            source=request.path_params["source"],
            limit=_limit,
        )
        _res = []
        for _e in _events:
            _res.append(
                {
                    **_e,
                    "created_at": shape.local_iso_text(_e.get("created_at"), self._zone),
                }
            )
        return JsonResponse(_res)

    def dataset_page(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _client: NodeClient = self._client(_node)
        _tab: str = request.query_params.get("tab", _TABS[0])
        if _tab not in _TABS:
            _tab = _TABS[0]

        _info: dict[str, Any] = _client.get_dataset(_source, _dataset)
        _context: dict[str, Any] = {
            "page": "dataset",
            "node": _node,
            "nav": self._nav(_client),
            "source": _source,
            "dataset": _dataset,
            "info": _info,
            "facts": shape.facts(_info),
            "tab": _tab,
            "tabs": _TABS,
        }
        if _tab == "partitions":
            _update = self._partitions(
                _client,
                _source,
                _dataset,
            )
            _context.update(_update)
        elif _tab == "quality":
            _update = self._qualities(
                _client,
                _source,
                _dataset,
                request.query_params.get("only") == "issues",
            )
            _context.update(_update)
        elif _tab == "definitions":
            _context["groups"] = _client.list_definitions(
                source=_source,
                dataset=_dataset,
            )
        else:
            _context["runs"] = _client.list_runs(
                _source,
                _dataset,
                limit=_RUN_LIMIT,
            )
        return self._render(
            request,
            "dataset.html",
            **_context,
        )

    @staticmethod
    def _qualities(
        client: NodeClient,
        source: str,
        dataset: str,
        only_issues: bool,
    ) -> dict[str, Any]:
        _records: list[dict[str, Any]] = client.list_qualities(source, dataset)
        _newest = shape.newest(
            _records,
            _MAX_LISTED,
            key=lambda r: r["assetfile"].get("modified_at") or 0,
        )
        _counts: dict[str, int] = {
            "ok": 0,
            "warn": 0,
            "bad": 0,
            "missing": 0,
        }
        _rows: int = 0
        _items: list[dict[str, Any]] = []
        for _record in _newest:
            _file: dict[str, Any] = _record["assetfile"]
            _view = shape.quality_view(_record.get("quality"))
            if _view is None:
                _counts["missing"] += 1
            else:
                _counts[_view["status"]] += 1
                _rows += _view["height"]
            if only_issues and _view is not None and _view["status"] == "ok":
                continue
            _apd: dict[str, Any] = {
                "partitions": _file.get("partitions"),
                "file": _file.get("name"),
                "view": _view,
            }
            _items.append(_apd)
        return {
            "items": _items,
            "total": len(_records),
            "counts": _counts,
            "rows_total": _rows,
            "only_issues": only_issues,
        }

    @staticmethod
    def _partitions(
        client: NodeClient,
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        _files: list[dict[str, Any]] = client.list_assetfiles(source, dataset)
        _keys: dict[str, set[str]] = {}
        _size: int = 0
        _latest: float | None = None
        for _file in _files:
            _size += _file.get("size") or 0
            _stamp = _file.get("modified_at")
            if isinstance(_stamp, (int, float)) and (_latest is None or _stamp > _latest):
                _latest = _stamp
            for _k, _v in (_file.get("partitions") or {}).items():
                _keys.setdefault(_k, set()).add(str(_v))
        _spans: list[dict[str, Any]] = []
        for _k, _values in _keys.items():
            _ordered: list[str] = sorted(_values)
            _apd: dict[str, Any] = {
                "key": _k,
                "count": len(_ordered),
                "first": _ordered[0],
                "last": _ordered[-1],
            }
            _spans.append(_apd)
        return {
            "files": shape.newest(
                _files,
                _MAX_LISTED,
                key=lambda f: f.get("modified_at") or 0,
            ),
            "total": len(_files),
            "size": _size,
            "latest": _latest,
            "spans": _spans,
        }

    # --------------------------------------------------
    # Runs
    # --------------------------------------------------

    async def submit_run(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _source: str = request.path_params["source"]
        _dataset: str = request.path_params["dataset"]
        _client: NodeClient = self._client(_node)
        _body: dict[str, Any] = await self._json_body(request, _MAX_FORM_BYTES * 16)

        # The node checks that params is an object
        _params: Any = _body.get("params")
        _run: dict[str, Any] = await run_in_threadpool(
            _client.submit_dataset_run,
            _source,
            _dataset,
            _params,
        )
        self._log.info(
            "dataset run submitted from web",
            metadata={
                "user": self._principal(request).name,
                "node": _node,
                "dataset": f"{_source}.{_dataset}",
                "run": _run.get("id"),
            },
        )
        return JsonResponse(_run, status_code=202)

    def get_run(self, request: Request) -> Response:
        _client: NodeClient = self._client(request.path_params["node"])
        _run: dict[str, Any] = _client.get_dataset_run(
            request.path_params["source"],
            request.path_params["dataset"],
            request.path_params["id"],
        )
        return JsonResponse(_run)

    # --------------------------------------------------
    # Query
    # --------------------------------------------------

    def query_page(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _client: NodeClient = self._client(_node)
        return self._render(
            request,
            "query.html",
            page="query",
            node=_node,
            nav=self._nav(_client),
        )

    async def query(self, request: Request) -> Response:
        _node: str = request.path_params["node"]
        _client: NodeClient = self._client(_node)
        _body: dict[str, Any] = await self._json_body(request, _MAX_SQL_CHARS * 4)
        _sql: Any = _body.get("sql")
        if not isinstance(_sql, str) or not _sql.strip():
            raise NodeBadRequestError("'sql' must be a non-empty string")
        if len(_sql) > _MAX_SQL_CHARS:
            raise NodeBadRequestError("'sql' is too long")

        # The web host holds one identity on the node
        # so every query of the console shares one session
        _result = await run_in_threadpool(_client.query, _sql)
        self._log.info(
            "query from web",
            metadata={
                "user": self._principal(request).name,
                "node": _node,
                "sql": _sql[:500],
                "rows": len(_result.rows),
                "elapsed_ms": _result.elapsed_ms,
            },
        )
        return JsonResponse(_result)

    # --------------------------------------------------
    # Errors
    # --------------------------------------------------

    @staticmethod
    def _wants_page(request: Request) -> bool:
        return "text/html" in request.headers.get("accept", "")

    def _answer(
        self,
        request: Request,
        status: int,
        error: str,
        message: str,
    ) -> Response:
        if self._wants_page(request):
            return self._render(
                request,
                "error.html",
                status=status,
                status_code=status,
                message=message,
            )
        _res: dict[str, Any] = {"error": error, "message": message}
        return JsonResponse(_res, status_code=status)

    def _on_known_error(self, request: Request, exc: Exception) -> Response:
        _status: int = 500
        for _type in type(exc).__mro__:
            if _type in _STATUS:
                _status = _STATUS[_type]
                break
        return self._answer(request, _status, type(exc).__name__, _describe(exc))

    def _on_http_error(self, request: Request, exc: Exception) -> Response:
        _status: int = exc.status_code if isinstance(exc, HTTPException) else 500
        _message: str = "Not found" if _status == 404 else "Request refused"
        return self._answer(request, _status, "http error", _message)

    def _on_unexpected_error(self, request: Request, exc: Exception) -> Response:
        self._log.error(
            f"unhandled {type(exc).__name__}: {request.method} {request.url.path}",
            metadata={"error": type(exc).__name__},
        )
        return self._answer(request, 500, "internal error", "Internal error")
