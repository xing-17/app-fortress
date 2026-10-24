from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.internal.logstream import LogStream
from app.internal.util.stopwatch import IStopwatch
from app.service.node.client.node import NodeClient
from app.service.node.dra import (
    DRABusyError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeRunNotFoundError,
    NodeSourceNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
)

from .instructions import (
    _GET_QUALITY_DOC,
    _GET_RUN_DOC,
    _GET_SCHEMA_DOC,
    _INSTRUCTIONS,
    _LIST_DATASETS_DOC,
    _LIST_MACHINE_SNAPSHOTS_DOC,
    _LIST_NODES_DOC,
    _LIST_RUNS_DOC,
    _QUERY_DOC,
)

T = TypeVar("T")

_MAX_LOGGED_SQL = 500
_DEFAULT_QUALITY_LIMIT = 20
_MAX_QUALITY_LIMIT = 200
_DEFAULT_RUN_LIMIT = 20
_MAX_RUN_LIMIT = 100

# The node words these for the caller
# AI sees them as they are and can adjust its next call
_CALLER_ERRORS = (
    NodeSourceNotFoundError,
    NodeDatasetNotFoundError,
    NodeRunNotFoundError,
    NodeBadRequestError,
    DRARejectedError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRABusyError,
)

# Not a node failure: the node answered that it does not hold the thing asked for
_NOT_FOUND = (NodeSourceNotFoundError, NodeDatasetNotFoundError)


class MCPGuard:
    """
    Runs one tool call: times it, logs it, and turns every failure into a `ToolError`

    Errors worded for the caller pass through with their message. Anything about the node itself
    (token, network, unexpected) gets a fixed message and the detail goes to the log only.

    """

    def __init__(
        self,
        log: LogStream,
    ) -> None:
        self._log = log

    def run(
        self,
        tool: str,
        arguments: dict[str, Any],
        func: Callable[[], T],
        metrics: Callable[[T], dict[str, float]] | None = None,
        caller: str | None = None,
    ) -> T:
        _meta: dict[str, Any] = {
            "tool": tool,
            "arguments": self._clip(arguments),
        }
        if caller is not None:
            _meta["caller"] = caller

        # Mark the start of the tool call in the log
        self._log.info(
            f"tool start: {tool}",
            metadata=_meta,
        )
        IStopwatch.tick()

        # Run the tool function and handle errors appropriately
        # Do not trim the error message for caller errors
        try:
            _res: T = func()
        except _CALLER_ERRORS as e:
            self._failed(_meta, e, IStopwatch.tock())
            raise ToolError(str(e)) from e
        except NodeUnauthorizedError as e:
            self._failed(_meta, e, IStopwatch.tock())
            _msg: str = "The node rejected the token of this host."
            raise ToolError(_msg) from e
        except NodeUnavailableError as e:
            self._failed(_meta, e, IStopwatch.tock())
            _msg: str = "The node is unreachable or too slow, try again later."
            raise ToolError(_msg) from e
        except Exception as e:
            self._failed(_meta, e, IStopwatch.tock())
            _msg: str = "Unexpected error in the node host."
            raise ToolError(_msg) from e

        # Log the successful tool call with elapsed time
        _elapsed_ms: float = round(IStopwatch.tock() * 1000, 3)
        _values: dict[str, float] = {"elapsed_ms": _elapsed_ms}
        if metrics is not None:
            _values.update(metrics(_res))

        self._log.info(
            f"tool ok: {tool}",
            metadata=_meta,
            metrics=_values,
        )
        return _res

    def _failed(
        self,
        metadata: dict[str, Any],
        error: Exception,
        elapsed: float,
    ) -> None:
        _meta: dict[str, Any] = {
            **metadata,
            "error": type(error).__name__,
        }
        self._log.warning(
            f"tool failed: {metadata['tool']}",
            metadata=_meta,
            metrics={"elapsed_ms": round(elapsed * 1000, 3)},
        )

    @staticmethod
    def _clip(arguments: dict[str, Any]) -> dict[str, Any]:
        _res: dict[str, Any] = {}
        for _key, _value in arguments.items():
            if _value is None:
                continue
            if isinstance(_value, str) and len(_value) > _MAX_LOGGED_SQL:
                _value = _value[:_MAX_LOGGED_SQL]
            _res[_key] = _value
        return _res


def _caller_of(ctx: Context) -> str | None:
    # No HTTP request (in-process transport) means no authenticated user
    _request = ctx.request_context.request
    if _request is None:
        return None
    _principal = _request.scope.get("state", {}).get("principal")
    return _principal.name if _principal is not None else None


def _split(dataset: str) -> tuple[str, str]:
    # Split a dataset string into source and name components
    _source, _dot, _name = dataset.strip().partition(".")
    if not _dot or not _source or not _name or "." in _name:
        raise NodeBadRequestError(f"dataset must be '<source>.<dataset>', got {dataset!r}")
    return _source, _name


def _partition_range(partitions: list[dict[str, str]]) -> dict[str, list[str]]:
    _keys: set[str] = set()
    for _p in partitions:
        _keys.update(_p)
    _res: dict[str, list[str]] = {}
    for _key in sorted(_keys):
        _values: list[str] = [_p[_key] for _p in partitions if _key in _p]
        _res[_key] = [min(_values), max(_values)]
    return _res


def _summarize_quality(item: dict[str, Any]) -> dict[str, Any]:
    # Can not return all quality details
    # only summarize key metrics
    _file: dict[str, Any] = item["assetfile"]
    _res: dict[str, Any] = {
        "partitions": _file["partitions"],
        "name": _file["name"],
    }
    _quality: dict[str, Any] | None = item["quality"]
    if _quality is None:
        _res["checked"] = False
        return _res

    _columns: list[dict[str, Any]] = _quality.get("columns", [])

    # Summarize null rates for columns with non-zero null rate
    _null_rate: dict[str, float] = {}
    for c in _columns:
        if c["null_rate"] > 0:
            _null_rate[c["name"]] = c["null_rate"]

    # Summarize constant columns for columns that are constant but not all null
    _constant_columns: list[str] = []
    for c in _columns:
        if c["is_constant"] and not c["is_all_null"]:
            _constant_columns.append(c["name"])

    # Summarize all-null columns for columns that are entirely null
    _all_null_columns: list[str] = []
    for c in _columns:
        if c["is_all_null"]:
            _all_null_columns.append(c["name"])

    _res.update(
        {
            "checked": True,
            "rows": _quality["height"],
            "complete_rows": _quality["complete_rows"],
            "duplicate_rows": _quality["duplicate_rows"],
            "null_rates": _null_rate,
            "constant_columns": _constant_columns,
            "all_null_columns": _all_null_columns,
        }
    )
    return _res


@dataclass(frozen=True)
class _Outcome:
    node: str
    value: Any = None
    error: Exception | None = None


def _failure_reason(error: Exception) -> str:
    # Fixed words, the detail (endpoint, message) stays in the log
    if isinstance(error, NodeUnauthorizedError):
        return "The node rejected the token of this host."
    if isinstance(error, NodeUnavailableError):
        return "The node is unreachable or too slow."
    return "Unexpected error in the node host."


class NodeRouter:
    """
    Picks the node of a call and asks all nodes at once for the tools that span them

    A node that fails is reported in its `_Outcome`, it never fails the others.

    """

    def __init__(
        self,
        clients: Mapping[str, NodeClient],
        log: LogStream,
    ) -> None:
        if not clients:
            raise ValueError("at least one node client is required")
        self._clients: dict[str, NodeClient] = dict(clients)
        self._log = log

    @property
    def names(self) -> list[str]:
        return list(self._clients)

    def get(self, node: str | None) -> tuple[str, NodeClient]:
        if node is None:
            if len(self._clients) == 1:
                return next(iter(self._clients.items()))
            _msg: str = f"several nodes are served, pass `node`, one of {self.names}"
            raise NodeBadRequestError(_msg)
        if node not in self._clients:
            _msg: str = f"unknown node {node!r}, one of {self.names}"
            raise NodeBadRequestError(_msg)
        return node, self._clients[node]

    def fan_out(
        self,
        func: Callable[[NodeClient], Any],
        node: str | None = None,
    ) -> list[_Outcome]:
        if node:
            _items: list[tuple[str, NodeClient]] = [self.get(node)]
        else:
            _items: list[tuple[str, NodeClient]] = list(self._clients.items())

        def _run(item: tuple[str, NodeClient]) -> _Outcome:
            _name, _client = item
            try:
                return _Outcome(_name, value=func(_client))
            except Exception as e:
                return _Outcome(_name, error=e)

        with ThreadPoolExecutor(max_workers=len(_items)) as _pool:
            _res: list[_Outcome] = list(_pool.map(_run, _items))

        for _o in _res:
            if _o.error is not None and not isinstance(_o.error, _NOT_FOUND):
                self._log.warning(
                    f"node failed: {_o.node}",
                    metadata={"node": _o.node, "error": type(_o.error).__name__},
                )
        return _res

    def locate(
        self,
        source: str,
        name: str,
        node: str | None = None,
    ) -> tuple[str, NodeClient]:
        # Single node or a named node needs no probing, the node answers for itself
        if node is not None or len(self._clients) == 1:
            return self.get(node)

        _dataset: str = f"{source}.{name}"
        _outcomes: list[_Outcome] = self.fan_out(lambda c: c.get_dataset(source, name))
        _found: list[str] = []
        for o in _outcomes:
            if o.error is None:
                _found.append(o.node)

        _down: list[str] = []
        for o in _outcomes:
            if o.error is not None and not isinstance(o.error, _NOT_FOUND):
                _down.append(o.node)

        # Exactly one node has the dataset, return
        if len(_found) == 1:
            return self.get(_found[0])

        # Multiple nodes have the dataset, ambiguous
        if len(_found) > 1:
            _msg: str = f"dataset '{_dataset}' is on nodes {_found}, pass `node` to choose one"
            raise NodeBadRequestError(_msg)

        # Some nodes were down
        if _down:
            _msg = f"dataset '{_dataset}' was not found, nodes not answering: {_down}"
            raise NodeBadRequestError(_msg)

        # No nodes have the dataset and no nodes were down
        # report not found on any node
        _msg = f"Dataset '{_dataset}' not found on any node"
        raise NodeDatasetNotFoundError(_msg)


def build_server(
    clients: Mapping[str, NodeClient],
    log: LogStream,
    name: str = "fortress",
) -> MCPServer:
    """
    Build the MCP server whose tools answer from `clients`

    The tools are plain `def` functions, the SDK runs them in a worker thread so a slow node
    call does not block the event loop. `list_nodes` and `list_datasets` ask every node at once,
    the other tools go to one node: the `node` argument, else the node that holds the dataset.

    Args:
    ----------
        clients (Mapping[str, NodeClient]):
            The nodes the tools talk to, by node name
        log (LogStream):
            Call trace: tool, arguments, elapsed time, rows and whether the result was truncated
        name (str):
            Server name announced to the MCP client

    """
    _server = MCPServer(name, instructions=_INSTRUCTIONS)
    _guard = MCPGuard(log)
    _router = NodeRouter(clients, log)

    @_server.tool(name="list_nodes", description=_LIST_NODES_DOC)
    def list_nodes(ctx: Context) -> list[dict[str, Any]]:
        def _call() -> list[dict[str, Any]]:
            _res: list[dict[str, Any]] = []
            for _o in _router.fan_out(lambda c: c.list_sources()):
                _entry: dict[str, Any] = {"name": _o.node, "reachable": _o.error is None}
                if _o.error is None:
                    _entry["sources"] = [s["name"] for s in _o.value]
                else:
                    _entry["error"] = _failure_reason(_o.error)
                _res.append(_entry)
            return _res

        return _guard.run(
            tool="list_nodes",
            arguments={},
            func=_call,
            metrics=lambda r: {"nodes": len(r), "unreachable": sum(not n["reachable"] for n in r)},
            caller=_caller_of(ctx),
        )

    @_server.tool(name="list_datasets", description=_LIST_DATASETS_DOC)
    def list_datasets(ctx: Context, source: str | None = None, node: str | None = None) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _outcomes: list[_Outcome] = _router.fan_out(lambda c: c.list_datasets(source), node)
            _datasets: list[dict[str, Any]] = []
            _nodes: list[dict[str, Any]] = []
            _missing: int = 0
            for _o in _outcomes:
                _entry: dict[str, Any] = {"name": _o.node, "reachable": True}
                if _o.error is None:
                    for _d in _o.value:
                        _datasets.append(
                            {
                                "node": _o.node,
                                "dataset": _d["dataset"],
                                "description": _d["description"],
                                "frequency": _d["frequency"],
                                "partition_keys": _d["partitions"],
                            }
                        )
                elif isinstance(_o.error, NodeSourceNotFoundError):
                    _missing += 1
                else:
                    _entry["reachable"] = False
                    _entry["error"] = _failure_reason(_o.error)
                _nodes.append(_entry)
            if _missing == len(_outcomes):
                raise NodeSourceNotFoundError(f"Source '{source}' not found on any node")
            return {"datasets": _datasets, "nodes": _nodes}

        return _guard.run(
            tool="list_datasets",
            arguments={"source": source, "node": node},
            func=_call,
            metrics=lambda r: {"datasets": len(r["datasets"])},
            caller=_caller_of(ctx),
        )

    @_server.tool(name="get_schema", description=_GET_SCHEMA_DOC)
    def get_schema(ctx: Context, dataset: str, node: str | None = None) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _node, _client = _router.locate(_source, _name, node)
            _info = _client.get_dataset(_source, _name)
            _groups = _client.list_definitions(_source, _name)
            _definitions = []
            for _g in _groups:
                _definition = {
                    "columns": [{"name": c["name"], "type": c["type"]} for c in _g["columns"]],
                    "partition_count": len(_g["partitions"]),
                    "partition_range": _partition_range(_g["partitions"]),
                }
                _definitions.append(_definition)

            _definitions.sort(
                key=lambda d: d["partition_count"],
                reverse=True,
            )
            return {
                "node": _node,
                "dataset": _info["dataset"],
                "description": _info["description"],
                "partition_keys": _info["partitions"],
                "definitions": _definitions,
            }

        return _guard.run(
            tool="get_schema",
            arguments={"dataset": dataset, "node": node},
            func=_call,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="get_quality", description=_GET_QUALITY_DOC)
    def get_quality(
        ctx: Context,
        dataset: str,
        limit: int = _DEFAULT_QUALITY_LIMIT,
        node: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _limit: int = max(1, min(limit, _MAX_QUALITY_LIMIT))
            _node, _client = _router.locate(_source, _name, node)
            _items = _client.list_qualities(_source, _name)
            _items.sort(key=lambda i: i["assetfile"].get("modified_at") or 0, reverse=True)
            return {
                "node": _node,
                "dataset": f"{_source}.{_name}",
                "total_files": len(_items),
                "files": [_summarize_quality(i) for i in _items[:_limit]],
            }

        return _guard.run(
            "get_quality",
            {"dataset": dataset, "limit": limit, "node": node},
            _call,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="list_runs", description=_LIST_RUNS_DOC)
    def list_runs(
        ctx: Context,
        dataset: str,
        status: str | None = None,
        limit: int = _DEFAULT_RUN_LIMIT,
        node: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _limit: int = max(1, min(limit, _MAX_RUN_LIMIT))
            _node, _client = _router.locate(_source, _name, node)
            _runs = _client.list_runs(_source, _name, status=status, limit=_limit)
            return {
                "node": _node,
                "dataset": f"{_source}.{_name}",
                "runs": _runs,
            }

        return _guard.run(
            tool="list_runs",
            arguments={"dataset": dataset, "status": status, "limit": limit, "node": node},
            func=_call,
            metrics=lambda r: {"runs": len(r["runs"])},
            caller=_caller_of(ctx),
        )

    @_server.tool(name="get_dataset_run", description=_GET_RUN_DOC)
    def get_dataset_run(
        ctx: Context,
        dataset: str,
        id: str,
        node: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _node, _client = _router.locate(_source, _name, node)
            _run = _client.get_dataset_run(_source, _name, id)
            return {
                "node": _node,
                "dataset": f"{_source}.{_name}",
                "run": _run,
            }

        return _guard.run(
            tool="get_dataset_run",
            arguments={"dataset": dataset, "id": id, "node": node},
            func=_call,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="list_machine_snapshots", description=_LIST_MACHINE_SNAPSHOTS_DOC)
    def list_machine_snapshots(
        ctx: Context,
        hours: float | None = None,
        node: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            # `not > 0` also rejects NaN
            if hours is not None and not hours > 0:
                raise NodeBadRequestError("'hours' must be greater than 0")
            _nodes: list[dict[str, Any]] = []
            for _o in _router.fan_out(lambda c: c.list_machine_snapshots(hours), node):
                _entry: dict[str, Any] = {"name": _o.node, "reachable": _o.error is None}
                if _o.error is None:
                    _entry["snapshots"] = _o.value
                else:
                    _entry["error"] = _failure_reason(_o.error)
                _nodes.append(_entry)
            return {"nodes": _nodes}

        def _metrics(result: dict[str, Any]) -> dict[str, float]:
            _count: int = sum(len(n.get("snapshots", [])) for n in result["nodes"])
            return {"snapshots": _count}

        return _guard.run(
            tool="list_machine_snapshots",
            arguments={"hours": hours, "node": node},
            func=_call,
            metrics=_metrics,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="query", description=_QUERY_DOC)
    def query(ctx: Context, sql: str, node: str | None = None) -> dict[str, Any]:
        _caller: str | None = _caller_of(ctx)

        def _call() -> dict[str, Any]:
            _node, _client = _router.get(node)
            _query: dict[str, Any] = _client.query(sql, caller=_caller).export()
            _query["node"] = _node
            return _query

        def _metrics(result: dict[str, Any]) -> dict[str, float]:
            return {
                "rows": len(result["rows"]),
                "truncated": float(bool(result["truncated"])),
            }

        return _guard.run(
            tool="query",
            arguments={"sql": sql, "node": node},
            func=_call,
            metrics=_metrics,
            caller=_caller,
        )

    return _server
