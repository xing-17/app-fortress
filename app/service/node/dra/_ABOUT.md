# service/node/dra

**DRA** (Data Research and Analytics) is the extension built into every node. It lets a caller query and analyse the node's data **without ever touching the data itself**: no file access, no download, no local setup. The caller sends one SELECT and gets rows back.

| File | Content |
|---|---|
| `session.py` | `DRASession`, a read-only DuckDB engine over mounted datasets |
| `pool.py` | `DRAPool`, bounded pool of sessions, one per caller |
| `guard.py` | `DRAGuard`, validation of statements, names and mounts |
| `limits.py` | `DRALimits`, resource limits of a session |
| `result.py` | Immutable result models (`DRADataResult`, `DRADefinitionResult`, ...) |
| `errors.py` | `DRAError` and its subclasses |
| `tests/` | Unit tests |

## Why

- **No workbench to manage.** An AI agent or a data analyst does not need to download files, set up an engine, or keep credentials for the storage. The node holds the data and the access; the caller holds a token.
- **Lightweight, fast access to global data.** Quick lookups, samples, aggregations and joins across the datasets a node serves, from anywhere, through the same call.
- **Safe by construction.** Because the caller never gets the files, the node decides what is readable, how much comes back, and how long a query may run.

## Scope (what DRA is not)

DRA is for **light, interactive queries**. Heavy analytics apps and systems (large scans, long pipelines, model training, bulk export, write-back) are **not supported, and should not be**. If a task hits the row, size, time or memory caps, it belongs in a dedicated analytics system, not here. Do not raise limits to make it fit.

## Components and how they work together

```
caller ─► NodeService.query(principal, sql)
              │
              ▼
          DRAPool.lease(principal.name) ──► DRASession (one per caller, built on first use)
                                                 │  DRAGuard.check_statement  (one SELECT only)
                                                 │  DuckDB, locked, views over mounts
                                                 ▼
                                             DRADataResult (capped, timed)
```

1. **Mounts.** `NodeService` turns every parquet dataset into a `DRAMount` and builds a session from them. Each mount becomes a view `<source>.<dataset>`, queryable as is in SQL. Declared partition keys are exposed as VARCHAR columns.
2. **`DRAGuard`** re-validates everything on the DRA side, the input is not trusted: identifiers (`[a-z_][a-z0-9_]*`, max 63), reserved schema names, mount schemes (`file`, `s3`), absolute paths with no `..`, patterns that stay inside their scope, and statements (exactly one, and it must be a SELECT).
3. **`DRASession`** owns an in-memory DuckDB engine. It is configured and then locked: external access off, directory access limited to the mount scopes, no extension autoload, no spilling to disk, memory and thread limits set. All mounts must be given up front. S3 credentials live in engine secrets and can be replaced with `refresh()` without rebuilding; errors never carry them.
4. **`DRALimits`** bounds one session: `timeout_seconds` (120), `max_rows` (10 000), `max_result_mb` (128), `memory_limit_mb` (1024), `threads` (2). Over the row or size cap the result is cut and marked `truncated` (`truncated_by` is `rows` or `size`); over the timeout the query is interrupted.
5. **`DRAPool`** keeps at most `max_sessions` sessions, one per key (the caller's principal name, so callers are isolated). A new key evicts the least recently used idle session; idle ones expire after `max_idle_seconds`. A leased session is never evicted; when all are leased a new key gets `DRABusyError`. `reset()` closes idle sessions and retires busy ones.
6. **Results** are frozen pydantic models, so they are safe to share and serialise.

## Errors

| Error | Meaning |
|---|---|
| `DRARejectedError` | Refused before reaching the engine (not a single SELECT, bad name or mount) |
| `DRAQueryError` | The engine failed the query (syntax, missing column, out of memory, ...) |
| `DRAQueryTimeoutError` | Interrupted by `timeout_seconds` |
| `DRABusyError` | Every session slot is running a query, retry later |
| `DRARefreshError` | Credentials could not be refreshed, the message never holds them |
| `DRAError` | Base class |

## Constraints

- **One SELECT per call.** No DDL, DML, `COPY`, `ATTACH`, `PRAGMA`, or multi-statement input.
- **Read-only, confined.** Reads stay inside the mount scopes. Do not loosen the engine lock or the guard.
- **Mounts are fixed per session.** A changed mount set needs a new session (`refresh()` rejects it).
- **Parquet only** for now, over `file` and `s3` schemes.
- **Never leak secrets.** Not in messages, logs or errors; the engine keeps only a digest of what a secret holds.
- **Results are capped.** Always check `truncated`; a truncated result is a sample, not the answer.
- **Keep the client timeout above `timeout_seconds`**, so the node answers a slow query with a timeout error.
- **Callers share a session per identity.** Isolation is per principal, not per request.
- **Do not use `DRASession` directly from hosts.** Go through `NodeService` / `NodeClient`, which handle identity, pooling, credential refresh and logging.

## Usage

Hosts use DRA through a `NodeClient` (see [../client/_ABOUT.md](../client/_ABOUT.md)); the node builds sessions on demand.

```python
from app.service.node.client import HttpNodeClient
from app.service.node.dra import DRAQueryError, DRARejectedError

with HttpNodeClient(endpoint="http://127.0.0.1:8800", token="<token>") as node:
    # 1. Discover what can be queried
    for ds in node.list_datasets():
        print(ds)  # names are "<source>.<dataset>"

    # 2. Run one SELECT, `caller` is optional, it gives that caller its own session
    try:
        res = node.query(
            "SELECT symbol, avg(close) AS avg_close "
            "FROM market.daily_prices "
            "WHERE trade_date >= '2026-01-01' "
            "GROUP BY symbol ORDER BY avg_close DESC LIMIT 20",
            caller="analyst-agent",
        )
    except DRARejectedError as e:
        print("refused:", e)  # e.g. more than one statement, or not a SELECT
    except DRAQueryError as e:
        print("engine error:", e)
    else:
        print(res.columns, res.types)
        for row in res.rows:
            print(row)
        if res.truncated:
            print(f"cut by {res.truncated_by}, narrow the query")
```

`market.daily_prices` is illustrative; use the names returned by `list_datasets()`. In-process, `LocalNodeClient(service)` offers the same calls.
