# service/node/client

How a host service (mcphost, webhost) talks to one node, whatever the transport.

| File | Content |
|---|---|
| `node.py` | `NodeClient`, the abstract interface |
| `httpnode.py` | `HttpNodeClient`, talks to a remote node over `/internal/...` with a bearer token |
| `localnode.py` | `LocalNodeClient`, calls a `NodeService` in the same process |
| `tests/` | Unit tests of the three files above |

## Why

A host needs the same things from a node (browse the catalog, run a SELECT, check health), but the node may live in another process or machine, or in the same process (single-machine deployment, tests). Without this layer each host would hardcode HTTP routes, header names, token handling and error parsing, and could not run against an in-process node.

`NodeClient` is that seam: hosts depend on the interface, and the transport is picked once at wiring time.

## What it does

- **One interface, two transports.** Methods mirror `NodeService`: `list_sources`, `get_source`, `list_datasets`, `get_dataset`, `list_assetfiles`, `list_metadatas`, `list_qualities`, `list_definitions`, `query`, `health`, `close`. Context manager supported.
- **Same shapes, same errors.** Every implementation returns the same dicts and `DRADataResult`, and raises the same domain errors, so a host's error handling does not depend on the transport.
- **`HttpNodeClient`** maps method calls to `/internal/...` routes, authenticates with a bearer token, and turns the response back into what the node raised or returned.
- **`LocalNodeClient`** delegates straight to `NodeService`, no HTTP and no token.
- **Caller delegation.** `query(sql, caller=...)` says on whose behalf a host queries. The node names the principal `<identity>:<caller>`, so each caller gets its own DRA session. Over HTTP this is the `X-Fortress-Caller` header and only works if the token may delegate; locally the name is composed client-side. Without `caller`, all queries of one client share one DRA session.

## Errors

All implementations raise: `NodeSourceNotFoundError`, `NodeDatasetNotFoundError`, `NodeBadRequestError`, `DRARejectedError`, `DRAQueryError`, `DRAQueryTimeoutError`, `DRABusyError`.

`HttpNodeClient` also raises:

| Error | When |
|---|---|
| `NodeUnauthorizedError` | 401, the token is rejected |
| `NodeUnavailableError` | timeout or connection failure |
| `NodeUnknownError` | unexpected status, or a body that is not JSON |

Mapping order: if the body names a known error (`error` + `message`), that type is raised with the node's message; otherwise the status decides (400/413 bad request, 401 unauthorized, 408 query timeout, 503 busy, anything else unknown).

## Constraints

- **Interface first.** A new capability goes into `NodeClient` and both implementations, mirroring `NodeService`. Hosts type against `NodeClient`, never a concrete client.
- **Behaviour parity.** Implementations must not diverge in return shapes or in the shared errors. Transport-only errors stay in the remote one.
- **Read-only.** Catalog reads and one SELECT. No writes, no node administration.
- **No business logic.** Transport and translation only. Validation and authorization belong to the node.
- **Time window.** `since` / `until` are epoch seconds or a datetime. A naive datetime is sent as UTC, not in the node's zone.
- **Path safety.** Source and dataset names are percent-encoded, `/` included, so a name is always one path segment.
- **Secrets.** The token never appears in logs or `__repr__` (only the endpoint). An empty token raises `ValueError`; so does `from_setting` when the endpoint has no token.
- **Timeout.** `timeout_seconds` (default 60) must stay above the node's `dra.timeout_seconds`, so a slow query is answered by the node (408) and not cut off by the client.
- **Health is special.** `health()` accepts 503 as a valid answer, since it carries the state of a node that is not running. It must not require a healthy node.
- **Lifecycle.** `HttpNodeClient` closes the `httpx.Client` only if it created it; an injected one belongs to the caller. `LocalNodeClient` never owns the `NodeService`, `close` does nothing.
- **Import weight.** `LocalNodeClient` is not exported from `__init__.py` because it pulls in the node service and resource layer. Import it from `app.service.node.client.localnode`; the package stays light for remote-only hosts.
