# service/_common

Shared building blocks for every fortress service.

| File | Content |
|---|---|
| `_service.py` | `BaseService`, the lifecycle base class |
| `auth.py` | `TokenAuth`, `Principal`, `AuthError`: stateless bearer token auth |
| `access.py` | `AccessAuth`: verifies the identity assertion signed by Cloudflare Access |
| `http.py` | `BearerAuthMiddleware`, `JsonResponse` for ASGI services |

Narrative docs (flows, operations, troubleshooting) live in `docs/auth/`.

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

Two ways to prove who the caller is, both end in the same `Principal`:

| Credential | Verified by | Used by |
|---|---|---|
| `Authorization: Bearer <token>` | `TokenAuth.verify` | local clients, and host services talking to the node |
| `Cf-Access-Jwt-Assertion: <jwt>` | `AccessAuth.verify` | ChatGPT, which can only do OAuth (Cloudflare Access is the OAuth server) |

`BearerAuthMiddleware` picks the path, see [Middleware](#middleware).

### Modules

| Name | Role |
|---|---|
| `AuthSetting` / `TokenSetting` (`app/setting/service.py`) | Bearer config: `masterfile` and the token entries (`name`, `description`, `version`, `expires`, `revoked`, `delegate`) |
| `AccessSetting` / `AccessUserSetting` (`app/setting/service.py`) | Access config: `team_domain`, `audience`, `users` (`email` -> `name`) |
| `TokenAuth` | Derives tokens (`token`), verifies them (`verify`), reports status (`state`), creates the key file (`generate_master_file`) |
| `AccessAuth` | Verifies an Access assertion (`verify`) and maps its email to a `Principal` |
| `Principal` | Immutable caller identity: `name`, `description`, `delegate` |
| `AuthError` | Raised on rejection, the message is always `invalid token`, the real cause is in `.reason` |
| `TokenAuthState` | Immutable snapshot (setting, master key, entries, file stamps), swapped as a whole on reload |
| `BearerAuthMiddleware` (`http.py`) | ASGI middleware, puts the principal in `request.state.principal` |

### Bearer tokens

Nothing is stored, a token is derived from one master key and the entry name:

```
token = hex( HMAC-SHA256(masterkey, "fortress-token-v1:<name>:<version>") )   # 64 chars
```

- Rotate: bump the entry's `version`.
- Kill: set `revoked: true` or remove the entry.
- Expire: set `expires` (last valid day, UTC).
- `verify` compares against every entry with `hmac.compare_digest` and does not return early.
- Master key file: at least 32 chars, and on POSIX it must be `chmod 600`. `generate_master_file` creates it with `O_EXCL` and mode `0600`, and never overwrites.

### Hot reload

Pass `reload` (a callable returning a fresh `AuthSetting`) and optionally `watch` files. At most once per `reload_interval` (default 1s) the master key file and the watched files are stat-ed. On a change the setting and key are rebuilt, so revoke and rotation need no restart. If the reload fails, the previous state stays in force and the error is logged, so watch the log.

Only `TokenAuth` reloads. `AccessAuth` reads its setting once, a change of `access` needs a restart.

### Delegation

A token with `delegate: true` may send `X-Fortress-Caller: <name>` to act for a caller already authenticated by the host service. The principal becomes `<token>:<caller>`, and the delegated principal does not inherit `delegate`. The caller name must match `^[a-z0-9][a-z0-9-]{0,31}$`. Any other token sending that header is rejected, and so is every Access identity.

### Cloudflare Access

Cloudflare Access sits in front of the host as the OAuth server. For each request it lets through it adds `Cf-Access-Jwt-Assertion`, a JWT signed with the keys the team publishes at `https://<team_domain>/cdn-cgi/access/certs`.

`AccessAuth.verify` accepts an assertion only when all of these hold:

- the signature is valid for a published key, algorithm RS256 only (`none` and HS256 are rejected)
- `exp`, `iat`, `iss`, `aud` are all present, with 10 seconds of clock leeway
- `iss` is `https://<team_domain>` and `aud` is the AUD tag of the application
- `email` is present and (lowercased) one of `setting.users`; a service token has no email and is rejected

The result is `Principal(name=<users[].name>, description="Cloudflare Access")`.

Keys are fetched on first use and cached for 1 hour, an unknown key id refreshes the cache, a fetch has a 5 second timeout. A fetch that fails rejects the request, so no keys never means open. `AuthError.reason` carries only the exception class name, because a PyJWT message may quote the token.

### Middleware

`BearerAuthMiddleware(app, auth, log, public_paths=frozenset({"/health"}), access=None)`

```
lifespan or public path                  -> pass
access set and Cf-Access-Jwt-Assertion   -> AccessAuth.verify only, a bad one is 401, never falls back to bearer
otherwise                                -> Authorization: Bearer, TokenAuth.verify
then X-Fortress-Caller                   -> delegation rules, or pass the principal as is
```

- `AccessAuth.verify` fetches keys over the network, so it runs in a thread pool.
- A rejected caller always sees `401 {"error": "unauthorized"}` with `WWW-Authenticate: Bearer`. The real reason (`missing`, `malformed`, `mismatch`, `revoked`, `expired`, `delegation denied`, `malformed caller`, `access keys unavailable`, `access assertion <ErrorClass>`, `access identity missing`, `access identity not allowed`) goes only to the `auth rejected` audit log entry, with `path` and `client`.
- `access` is imported only for type checking, a service that does not use it does not need PyJWT (`pyjwt[crypto]` is a dependency of mcphost).

### Usage

Bearer tokens:

```python
from pathlib import Path

from app.service._common import AuthError, Principal, TokenAuth
from app.service._common.http import BearerAuthMiddleware
from app.setting.service import AuthSetting, TokenSetting

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
    watch=[Path("settings/services.yaml")],
)

token = auth.token("analyst")  # hand this to the client
principal = auth.verify(token)  # Principal, or raises AuthError

app = BearerAuthMiddleware(asgi_app, auth=auth, log=log)
```

With Cloudflare Access:

```python
from app.service._common.access import AccessAuth
from app.setting.service import AccessSetting

access_setting = AccessSetting(
    team_domain="<team>.cloudflareaccess.com",
    audience="<AUD tag of the Access application>",
    users=[{"email": "me@example.com", "name": "me"}],
)

app = BearerAuthMiddleware(asgi_app, auth=auth, log=log, access=AccessAuth(access_setting))
```

`AccessAuth(setting, keys=...)` takes any object with `get_signing_key_from_jwt(token)`, which is how the tests sign assertions with a local RSA key (`tests/assertions.py`).

Client call:

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:<port>/...
```

CLI for the token side (`--service node|mcphost`, default `node`):

```bash
fortress auth init          # create the master key file
fortress auth list          # state and expiry of each entry
fortress auth show <name>   # print a token
```

### Tests

```bash
pytest app/service/_common/tests
```

`test_auth_unit.py` covers the tokens, the master key file, hot reload and the middleware. `test_access_unit.py` covers the assertion checks and the middleware priority rules.
