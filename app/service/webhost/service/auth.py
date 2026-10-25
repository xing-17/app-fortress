from __future__ import annotations

import secrets
import threading
import time
from typing import TYPE_CHECKING
from urllib.parse import quote, urlsplit

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.internal.logstream import LogStream
from app.service._common.auth import AuthError, Principal
from app.service._common.http import JsonResponse

if TYPE_CHECKING:
    from app.service._common.access import AccessAuth

COOKIE_NAME = "fortress_session"
SESSION_TTL_SECONDS = 12 * 3600

_ASSERTION_HEADER = "cf-access-jwt-assertion"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def safe_next(value: str | None) -> str:
    """
    A path on this host to go to after login
    anything else (another host, a scheme) is dropped
    """
    if not value:
        return "/"
    if not value.startswith("/"):
        return "/"
    if value.startswith(("//", "/\\")):
        return "/"
    return value


class SessionStore:
    """
    Browser sessions kept in memory, the cookie holds only a random id

    A restart signs everybody out, and `drop` signs one out at once.

    Args:
    ----------
        ttl_seconds (float):
            Lifetime of a session
        max_sessions (int):
            Cap of live sessions, the oldest is dropped over it

    Methods:
    ----------
        create(principal) -> str:
            Open a session, returns its id
        get(sid) -> Principal | None:
            The principal of a live session
        drop(sid) -> None:
            Close a session

    """

    def __init__(
        self,
        ttl_seconds: float = SESSION_TTL_SECONDS,
        max_sessions: int = 256,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_sessions
        self._items: dict[str, tuple[Principal, float]] = {}
        self._lock = threading.Lock()

    def create(
        self,
        principal: Principal,
    ) -> str:
        # Clean up expired sessions and enforce max session limit
        _sid: str = secrets.token_urlsafe(32)
        _now: float = time.monotonic()
        with self._lock:
            _new: dict[str, tuple[Principal, float]] = {}
            for _k, _v in self._items.items():
                if _v[1] > _now:
                    _new[_k] = _v
            self._items = _new
            while len(self._items) >= self._max:
                self._items.pop(next(iter(self._items)))
            self._items[_sid] = (principal, _now + self._ttl)
        return _sid

    def get(
        self,
        sid: str | None,
    ) -> Principal | None:
        if not sid:
            return None
        with self._lock:
            _item = self._items.get(sid)
            if _item is None:
                return None
            if _item[1] <= time.monotonic():
                del self._items[sid]
                return None
            return _item[0]

    def drop(
        self,
        sid: str | None,
    ) -> None:
        if sid:
            with self._lock:
                self._items.pop(sid, None)


class SecurityHeadersMiddleware:
    """
    Headers for a console that loads nothing from outside.

    Header must not be framed or cached

    """

    _HEADERS: tuple[tuple[bytes, bytes], ...] = (
        (
            b"content-security-policy",
            b"default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        ),
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"same-origin"),
        (b"cache-control", b"no-store"),
    )

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        _static: bool = scope.get("path", "").startswith("/static/")

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                _headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                _present: set[bytes] = {k.lower() for k, _ in _headers}
                for _key, _value in self._HEADERS:
                    # Static files may be cached by the browser
                    if _static and _key == b"cache-control":
                        continue
                    if _key not in _present:
                        _headers.append((_key, _value))
                message = {**message, "headers": _headers}
            await send(message)

        await self._app(scope, receive, _send)


class WebAuthMiddleware:
    """
    Sign people in for the web console, put the `Principal` in `request.state.principal`

    A person is identified by, in this order: the Cloudflare Access assertion (when `access` is set
    and the header is there, a bad one is rejected and never falls back), else the session cookie
    opened by the login page. Anything else is sent to `/login` (a page) or answered 401 (a call).

    The `Host` must be loopback or one of `public_hosts`, and a request that changes something must not
    come from another origin.

    Args:
    ----------
        app (ASGIApp):
            Wrapped application
        sessions (SessionStore):
            Sessions opened by the login page
        log (LogStream):
            Audit log
        public_hosts (frozenset[str]):
            Host names (optionally with port) browsers reach this host by, besides loopback
        access (AccessAuth | None):
            Verifier of the Cloudflare Access assertion, None ignores the header

    """

    def __init__(
        self,
        app: ASGIApp,
        sessions: SessionStore,
        log: LogStream,
        public_hosts: frozenset[str] = frozenset(),
        access: AccessAuth | None = None,
    ) -> None:
        self._app = app
        self._sessions = sessions
        self._log = log
        self._public_hosts = public_hosts
        self._access = access

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        _request = Request(scope)
        _refused: Response | None = self._refuse(_request)
        if _refused is not None:
            await _refused(scope, receive, send)
            return

        _path: str = scope.get("path", "")
        if _path == "/login" or _path.startswith("/static/"):
            await self._app(scope, receive, send)
            return

        try:
            _found: tuple[Principal, str] | None = await self._identify(_request)
        except AuthError as e:
            self._log.warning(
                f"web auth rejected, reason: {e.reason}",
                metadata={"reason": e.reason, "path": _path, "client": self._client(scope)},
            )
            _response: Response = JsonResponse({"error": "unauthorized"}, status_code=401)
            await _response(scope, receive, send)
            return

        if _found is None:
            await self._deny(_request)(scope, receive, send)
            return

        _state: dict = scope.setdefault("state", {})
        _state["principal"], _state["via"] = _found
        await self._app(scope, receive, send)

    async def _identify(
        self,
        request: Request,
    ) -> tuple[Principal, str] | None:
        _assertion: str | None = request.headers.get(_ASSERTION_HEADER)
        if self._access is not None and _assertion is not None:
            # Fetching the signing keys is a blocking call
            _principal: Principal = await run_in_threadpool(self._access.verify, _assertion)
            return _principal, "access"

        _session: Principal | None = self._sessions.get(request.cookies.get(COOKIE_NAME))
        if _session is not None:
            return _session, "session"
        return None

    @staticmethod
    def _deny(request: Request) -> Response:
        _wants_page: bool = request.method in ("GET", "HEAD") and "text/html" in request.headers.get("accept", "")
        if not _wants_page:
            return JsonResponse({"error": "unauthorized"}, status_code=401)
        _target: str = request.url.path
        if request.url.query:
            _target += "?" + request.url.query
        return RedirectResponse(f"/login?next={quote(_target, safe='')}", status_code=303)

    def _refuse(
        self,
        request: Request,
    ) -> Response | None:
        _host: str = request.headers.get("host", "").lower()
        _name: str = urlsplit(f"//{_host}").hostname or ""
        if _host not in self._public_hosts and _name not in self._public_hosts and _name not in _LOOPBACK_HOSTS:
            return PlainTextResponse("misdirected request", status_code=421)

        if request.method not in _SAFE_METHODS:
            _origin: str | None = request.headers.get("origin")
            if _origin is not None and urlsplit(_origin).netloc.lower() != _host:
                return PlainTextResponse("cross-origin request refused", status_code=403)
        return None

    @staticmethod
    def _client(scope: Scope) -> str:
        _client = scope.get("client")
        return _client[0] if _client else "-"
