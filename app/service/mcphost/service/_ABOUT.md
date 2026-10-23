# service/mcphost/service

The **MCP front door of a node**. It lets an AI client (Claude, Copilot, ...) discover, inspect and query the datasets of one node through the [Model Context Protocol](https://modelcontextprotocol.io), over streamable HTTP.

The host holds **no data and no logic of its own**. Every tool is answered by a `NodeClient` (see [../../node/client/_ABOUT.md](../../node/client/_ABOUT.md)) talking to the [node service](../../node/service/_ABOUT.md). The host only does four things: authenticate the AI user, expose tools, translate errors for the AI, and leave an audit trail.

| File | Content |
|---|---|
| `service.py` | `McpHostService`, the lifecycle: pick the node, check it at start, build the MCP server, mount auth |
| `tools.py` | `build_server` (the four tools), `MCPGuard` (timing, logging, error translation), result shaping helpers |
| `instructions.py` | The texts the AI reads: server instructions and the description of each tool |
| `http.py` | `serve`: start the service, run uvicorn, stop the service |
| `tests/` | Unit tests (`fakes.py` holds a fake `NodeClient`) |

## Components

```
AI client ──► HTTP (streamable MCP)
                │
                ▼
        BearerAuthMiddleware ──► Principal (which user / device)
                │
                ▼
        MCPServer  (tools: list_datasets, get_schema, get_quality, query)
                │
                ▼
        MCPGuard   (log start, time, translate errors, log result)
                │
                ▼
        NodeClient (HttpNodeClient, or any NodeClient)
                │
                ▼
        Node service ─► catalog / DRA query
```

## Lifecycle (`McpHostService`)

1. **Construct**: choose the node from `setting.nodes`, the first one unless `node` names another (unknown name → `ValueError`). A ready-made `client` can be injected (tests, in-process); otherwise an `HttpNodeClient` is built from the node setting at start. `auth` is a `TokenAuth`, needed only for `asgi_app`.
2. **`start()`** (`_start`) fails fast on a bad deployment:
   - `client.health()` must say the node `is_running`. The health route needs no token, so this only proves the node is up.
   - `client.list_sources()` is called next. It needs the token, so this is what proves the host's token for the node is valid.
   - Then `build_server` creates the MCP server. If anything fails, the client the host created is released and the error is re-raised.
3. **`asgi_app(host)`** returns the Starlette app of the MCP server. It refuses to build when the service is not running, or when there is **no auth** (it would serve data to anyone). It adds `BearerAuthMiddleware` with **no public paths**: every route needs a token. `host` decides which `Host` headers the transport accepts.
4. **`stop()`** drops the server and closes the client, but only if the host created it. An injected client is never closed by the host.
5. **`health()`** adds the node's name, whether it is reachable and its state to the base service health.

`serve(service, host, port, log_level)` in `http.py` is the standard entry: `start()` → `uvicorn.run(asgi_app)` → `stop()` in `finally`. Host and port default to the setting (`127.0.0.1:8801`).

## Two layers of tokens

| Token | Held by | Checked by |
|---|---|---|
| **User token** (one per device) | The AI client | The host, `BearerAuthMiddleware` with `setting.auth` |
| **Host token** | The host | The node, its own auth |

The two master keys must differ: a user token is never accepted by the node. The authenticated `Principal` is stored on the request scope; `_caller_of(ctx)` reads its name for each tool call (`None` for an in-process transport without an HTTP request).

## Tools

The AI is guided to the flow `list_datasets` → `get_schema` → `query`, with `get_quality` to judge completeness. Datasets are always named `<source>.<dataset>`, which is also the table name in SQL (`_split` validates this form).

| Tool | Node calls | Returns |
|---|---|---|
| `list_datasets(source?)` | `list_datasets` | dataset, description, frequency, partition keys |
| `get_schema(dataset)` | `get_dataset`, `list_definitions` | Description, partition keys, and `definitions`: each distinct schema (columns and types) with its `partition_count` and the min/max of each partition key. Sorted by partition count, the most common schema first |
| `get_quality(dataset, limit=20)` | `list_qualities` | Per partition file, newest first (limit clamped 1..200): rows, complete rows, duplicates, columns with a NULL rate, constant columns, all-NULL columns. `checked: false` when a file has no quality record |
| `query(sql)` | `query(sql, caller=)` | The rows of ONE read-only SELECT (DuckDB). Capped in rows and size, `truncated` says so |

Notes:
- `_summarize_quality` reduces the full quality record to key metrics so the answer stays small for the AI.
- Partition keys are VARCHAR in SQL; the tool descriptions tell the AI to `CAST` them. Columns missing in some partitions read as NULL.
- The tool functions are plain `def`, the MCP SDK runs them in a worker thread so a slow node call does not block the event loop.
- **Read-only by construction**: there is no write tool, and SQL validation, session isolation, row/size caps and timeout are the node's DRA engine's job, not the host's.
- `query` passes the user's name as `caller`, so the node runs the query in a session of its own and audits it by that name.

## Error handling and logging (`MCPGuard`)

Every tool call runs through `MCPGuard.run`:

1. Log `tool start` with the tool, arguments (strings clipped to 500 chars, so long SQL cannot flood the log) and the caller.
2. Time the call.
3. On success log `tool ok` with `elapsed_ms` plus tool metrics (`datasets`; `rows` and `truncated` for `query`).
4. On failure log `tool failed` (warning) and raise a `ToolError`:

| Error from the node side | Message the AI gets |
|---|---|
| Source/dataset not found, bad request, SQL rejected, query failed, query timeout, all sessions busy | The **original message**: it is worded for the caller, so the AI can fix its next call |
| Node rejected the host token | Fixed: "The node rejected the token of this host." |
| Node unreachable or too slow | Fixed: "The node is unreachable or too slow, try again later." |
| Anything else | Fixed: "Unexpected error in the node host." |

Only caller-worded errors pass their text through. Anything about the host/node itself (token, network, bugs) is hidden from the AI and only goes to the log.

## Instructions (`instructions.py`)

The server instructions and each tool description are the AI's only manual, so they carry the rules that matter: dataset naming, VARCHAR partition keys, per-partition schema differences, single SELECT/WITH only (no writes, SET, ATTACH or file functions), results not saved, truncation, query timeout. Change behavior hints here, not in the tools.

## Design rules

- **No data, no SQL logic** in the host. If a rule is about data access, it belongs in the node.
- **One host, one node.** To serve several nodes, run several hosts.
- **Fail at start**, not at the first AI call: node down, wrong endpoint and wrong token are all caught by `start()`.
- **No auth, no app.** `asgi_app` never serves without a `TokenAuth`.
