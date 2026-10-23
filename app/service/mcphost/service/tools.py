from __future__ import annotations

from collections.abc import Callable
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
    NodeSourceNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
)

from .instructions import (
    _GET_QUALITY_DOC,
    _GET_SCHEMA_DOC,
    _INSTRUCTIONS,
    _LIST_DATASETS_DOC,
    _QUERY_DOC,
)

T = TypeVar("T")

_MAX_LOGGED_SQL = 500
_DEFAULT_QUALITY_LIMIT = 20
_MAX_QUALITY_LIMIT = 200

# The node words these for the caller
# AI sees them as they are and can adjust its next call
_CALLER_ERRORS = (
    NodeSourceNotFoundError,
    NodeDatasetNotFoundError,
    NodeBadRequestError,
    DRARejectedError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRABusyError,
)


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


def build_server(
    client: NodeClient,
    log: LogStream,
    name: str = "fortress",
) -> MCPServer:
    """
    Build the MCP server whose tools answer from `client`

    The tools are plain `def` functions, the SDK runs them in a worker thread so a slow node
    call does not block the event loop.

    Args:
    ----------
        client (NodeClient):
            The node the tools talk to
        log (LogStream):
            Call trace: tool, arguments, elapsed time, rows and whether the result was truncated
        name (str):
            Server name announced to the MCP client

    """
    _server = MCPServer(name, instructions=_INSTRUCTIONS)
    _guard = MCPGuard(log)

    @_server.tool(name="list_datasets", description=_LIST_DATASETS_DOC)
    def list_datasets(ctx: Context, source: str | None = None) -> list[dict[str, Any]]:
        def _call() -> list[dict[str, Any]]:
            _items = client.list_datasets(source)
            _res: list[dict[str, Any]] = []
            for _d in _items:
                _res.append(
                    {
                        "dataset": _d["dataset"],
                        "description": _d["description"],
                        "frequency": _d["frequency"],
                        "partition_keys": _d["partitions"],
                    }
                )
            return _res

        return _guard.run(
            tool="list_datasets",
            arguments={"source": source},
            func=_call,
            metrics=lambda r: {"datasets": len(r)},
            caller=_caller_of(ctx),
        )

    @_server.tool(name="get_schema", description=_GET_SCHEMA_DOC)
    def get_schema(ctx: Context, dataset: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _info = client.get_dataset(_source, _name)
            _groups = client.list_definitions(_source, _name)
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
                "dataset": _info["dataset"],
                "description": _info["description"],
                "partition_keys": _info["partitions"],
                "definitions": _definitions,
            }

        return _guard.run(
            tool="get_schema",
            arguments={"dataset": dataset},
            func=_call,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="get_quality", description=_GET_QUALITY_DOC)
    def get_quality(ctx: Context, dataset: str, limit: int = _DEFAULT_QUALITY_LIMIT) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            _source, _name = _split(dataset)
            _limit: int = max(1, min(limit, _MAX_QUALITY_LIMIT))
            _items = client.list_qualities(_source, _name)
            _items.sort(key=lambda i: i["assetfile"].get("modified_at") or 0, reverse=True)
            return {
                "dataset": f"{_source}.{_name}",
                "total_files": len(_items),
                "files": [_summarize_quality(i) for i in _items[:_limit]],
            }

        return _guard.run(
            "get_quality",
            {"dataset": dataset, "limit": limit},
            _call,
            caller=_caller_of(ctx),
        )

    @_server.tool(name="query", description=_QUERY_DOC)
    def query(ctx: Context, sql: str) -> dict[str, Any]:
        _caller: str | None = _caller_of(ctx)

        def _call() -> dict[str, Any]:
            _query: dict[str, Any] = client.query(sql, caller=_caller).export()
            return _query

        def _metrics(result: dict[str, Any]) -> dict[str, float]:
            return {
                "rows": len(result["rows"]),
                "truncated": float(bool(result["truncated"])),
            }

        return _guard.run(
            tool="query",
            arguments={"sql": sql},
            func=_call,
            metrics=_metrics,
            caller=_caller,
        )

    return _server
