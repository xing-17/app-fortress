# service/node/service

The **server side of a node**. It answers two kinds of questions from callers:

1. **Catalog**: what does this node hold? (sources, datasets, assetfiles, metadata, quality, definitions)
2. **Query**: run one SELECT over the node's data, through the [DRA](../dra/_ABOUT.md) engine.

Callers never read the data files; they ask the node, which owns the data and the access. Hosts normally reach it through a `NodeClient` (see [../client/_ABOUT.md](../client/_ABOUT.md)).

| File | Content |
|---|---|
| `service.py` | `NodeService`, the logic: catalog answers, DRA session management, query |
| `http.py` | `NodeHttp`, a thin Starlette mapping of `NodeService`; `create_app`, `serve` |
| `errors.py` | Node exceptions (`NodeSourceNotFoundError`, `NodeDatasetNotFoundError`, `NodeBadRequestError`, ...) |
| `tests/` | Unit tests |

## Components

```
HTTP request
    │
    ▼
BearerAuthMiddleware ──► Principal (who is calling)
    │
    ▼
NodeHttp  (routes, parameter parsing, exception ─► status code)
    │
    ▼
NodeService
    ├── catalog ──► GlobalSources ─► BaseSource ─► BaseDataset ─► assetfiles / metadata
    └── query   ──► DRAPool ─► DRASession (DuckDB)
```

- **`NodeService`** has no HTTP knowledge. It can be used in-process (`LocalNodeClient`) or behind `NodeHttp`.
- **`NodeHttp`** holds no logic: it parses `since` / `until`, calls the service, and maps exceptions to status codes (`404` unknown source/dataset, `400` bad request or rejected/failed query, `408` query timeout, `503` all sessions busy, `500` anything else with no detail in the body).
- **Auth** is done before any route except `GET /health`; the resulting `Principal` is passed to `query`.

## Catalog path (no DRA)

`list_sources`, `get_source`, `list_datasets`, `get_dataset`, `list_assetfiles`, `list_metadatas`, `list_qualities`, `list_definitions` are answered by the resources themselves (`GlobalSources` and the source/dataset objects). The DRA engine is not involved, so these never use a session and never hit the session limit.

`list_definitions` groups assetfiles by definition fingerprint and lists the partitions carrying each one; assetfiles without metadata or fingerprint are skipped.

## Query path (with DRA)

`NodeService` is the only owner of DRA on the node. It supplies what DRA needs and leaves the rest to DRA.

| Step | Who | What |
|---|---|---|
| 1. Mounts | `NodeService._mounts` | Every PARQUET dataset with at least one assetfile becomes a `DRAMount` named `<source>.<dataset>` (from `asset.get_dra_mount()`). Empty datasets are skipped, a view over no files cannot be created. |
| 2. Pool | `NodeService.__init__` | Builds `DRAPool` with `_build_session` as factory, `setting.dra.max_sessions`, `max_session_idle_seconds`, and `_log_session_closed` as `on_close`. |
| 3. Session build | `NodeService._build_session` | `setting.dra` is validated into `DRALimits`; a `DRASession(mounts, limits)` is created. All mounts are fixed at this point. |
| 4. Lease | `NodeService.query` | `pool.lease(caller.name)`: one session per principal, built on first use. Over capacity, the least recently used idle session is evicted; if all are busy, `DRABusyError`. |
| 5. Credential refresh | `NodeService._refresh_session` | Inside the lease, if the session holds secrets and `refresh_interval_seconds` has passed, mounts are re-resolved and `session.refresh(mounts)` replaces the credentials without a rebuild. Any non-DRA failure becomes `DRARefreshError` carrying only the exception type, never the secret. |
| 6. Execute | `DRASession.query` | `DRAGuard` checks one SELECT, the locked DuckDB runs it under `DRALimits` (timeout, rows, size, memory). Returns `DRADataResult`, possibly `truncated`. |
| 7. Log | `NodeService.query` | `DRAError` is logged as a warning (error type only) and re-raised; success is logged with `rows` and `elapsed_ms`. SQL is cut to 500 characters in the log. |

Other lifecycle links to the pool:

- `health()` merges `pool.stats()` (`sessions`, `busy_sessions`) into the service health.
- `reset_sessions()` calls `pool.reset()`: idle sessions closed, busy ones retired. `_stop` calls it, and it can be used after data or setting changes so the next query builds a new session with fresh mounts.

### Error flow

`DRARejectedError`, `DRAQueryError`, `DRAQueryTimeoutError` and `DRABusyError` pass through `NodeService` unchanged and `NodeHttp` maps them to `400`, `400`, `408`, `503`. Other `DRAError` subclasses (e.g. `DRARefreshError`) and unexpected exceptions become `500`; the body carries no detail and `NodeHttp` logs them.

`POST /internal/query` reads the body (max 1 MB, `413` above), requires `{"sql": "..."}`, and runs `NodeService.query` in the thread pool because DuckDB blocks.

## Constraints

- **The service must be running.** Every public method calls `_require_running`; otherwise `RuntimeError`.
- **Mounts are fixed per session.** A new dataset or assetfile appears only after `reset_sessions()` or session eviction.
- **Isolation is per principal**, not per request: concurrent calls from the same caller share one session.
- **Do not bypass the pool.** Never create a `DRASession` outside `NodeService`; identity, pooling, refresh and logging live here.
- **Keep the client timeout above `dra.timeout_seconds`**, so a slow query gets a `408` instead of a client-side cut.
- **No secrets in logs or errors.**

## Usage

```python
from app.service.node.service.http import serve

# Starts the service, serves over HTTP, stops the service on exit
serve(service, auth)
```

In tests or in-process, call `NodeService` directly:

```python
service.start()
service.list_datasets("market")
res = service.query(principal, "SELECT count(*) FROM market.daily_prices")
service.stop()
```

`market.daily_prices` is illustrative; use the names returned by `list_datasets()`.
