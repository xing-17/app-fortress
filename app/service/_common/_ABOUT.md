# service/_common

Shared building blocks for every fortress service.

| File | Content |
|---|---|
| `_service.py` | `BaseService`, the lifecycle base class |
| `auth.py` | `TokenAuth`, `Principal`, `AuthError`, bearer token auth |
| `http.py` | `BearerAuthMiddleware`, `JsonResponse` for ASGI services |

## BaseService

Base class of all services. It owns the lifecycle state machine and the logging, a concrete service only supplies the resource handling.

```
CREATED/STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED
STARTING/STOPPING -> FAILED  (when the hook raises)
```

Provided: `start()`, `stop()`, `health()`, and the properties `setting`, `log`, `state`, `is_running`. Both `start()` and `stop()` are idempotent and thread-safe.

A subclass must:

- set the class attribute `kind: ServiceKind`; the setting passed in must have the same kind, or `__init__` raises `ValueError`
- implement `_start()`: acquire resources and begin serving
- implement `_stop()`: release resources, must tolerate a partially started service
- optionally extend `health()`

## Auth

### How it works

Stateless bearer tokens. Nothing is stored, a token is derived from one master key and the entry name:

```
token = hex( HMAC-SHA256(masterkey, "fortress-token-v1:<name>:<version>") )   # 64 chars
```

- Rotate: bump the entry's `version`.
- Kill: set `revoked: true` or remove the entry.
- Expire: set `expires` (last valid day, UTC).
- `verify` compares against every entry in constant time. A rejected caller always sees `401 unauthorized`; the real reason (`missing`, `malformed`, `mismatch`, `revoked`, `expired`, `delegation denied`) goes only to the audit log via `AuthError.reason`.
- Master key file: at least 32 chars, and on POSIX it must be `chmod 600`.

### Modules

| Name | Role |
|---|---|
| `AuthSetting` / `TokenSetting` (`app/setting/service.py`) | Config: `masterfile` and the token entries (`name`, `description`, `version`, `expires`, `revoked`, `delegate`) |
| `TokenAuth` | Derives tokens (`token`), verifies them (`verify`), reports status (`state`), creates the key file (`generate_master_file`) |
| `Principal` | Immutable caller identity returned by `verify`: `name`, `description`, `delegate` |
| `AuthError` | Raised on rejection, message is always `invalid token` |
| `TokenAuthState` | Immutable snapshot (setting, master key, entries, file stamps), swapped as a whole on reload |
| `BearerAuthMiddleware` (`http.py`) | ASGI middleware: reads `Authorization: Bearer`, calls `verify`, puts the principal in `request.state.principal`, `/health` is public |

### Hot reload

Pass `reload` (a callable returning a fresh `AuthSetting`) and optionally `watch` files. At most once per `reload_interval` (default 1s) the master key file and the watched files are stat-ed. On a change the setting and key are rebuilt, so revoke and rotation need no restart. If the reload fails, the previous state stays in force and the error is logged, so watch the log.

### Delegation

A token with `delegate: true` may send `X-Fortress-Caller: <name>` to act for a caller already authenticated by the host service. The principal becomes `<token>:<caller>`, and the delegated principal does not inherit `delegate`. Any other token sending that header is rejected.

### Usage

```python
from pathlib import Path
from app.service._common import TokenAuth
from app.service._common.http import BearerAuthMiddleware

setting = AuthSetting(
    masterfile="../local/.auth/password.key",
    tokens=[TokenSetting(name="analyst", description="BI tool")],
)

# first deployment: create the key file (returns None if it exists)
TokenAuth.generate_master_file(setting, base_dir=Path("settings"))

auth = TokenAuth(
    setting,
    base_dir=Path("settings"),
    reload=load_auth_setting,  # optional, enables hot reload
    watch=[Path("settings/service.yaml")],
)

token = auth.token("analyst")  # hand this to the client
principal = auth.verify(token)  # Principal, or raises AuthError

app = BearerAuthMiddleware(asgi_app, auth=auth, log=log)
```

Client call:

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:<port>/...
```
