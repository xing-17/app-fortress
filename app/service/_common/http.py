from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic_core import to_json
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.internal.logstream import LogStream
from app.service._common.auth import AuthError, Principal, TokenAuth

if TYPE_CHECKING:
    # Not imported at runtime, the node does not need PyJWT
    from app.service._common.access import AccessAuth

_PUBLIC_PATHS = frozenset({"/health"})
_CALLER_HEADER = b"x-fortress-caller"
_ASSERTION_HEADER = b"cf-access-jwt-assertion"

# Same shape as a token name,
# delegated caller cannot smuggle in odd characters
_CALLER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}\Z")


class JsonResponse(Response):
    """
    JSON response serialized by pydantic, so datetime, Decimal and models are handled and
    NaN/Infinity (valid in a query result, not in JSON) become null

    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        _res: bytes = to_json(
            content,
            inf_nan_mode="null",
            bytes_mode="base64",
        )
        return _res


class BearerAuthMiddleware:
    """
    Reject requests without a valid bearer token, put the `Principal` in `request.state.principal`

    A token with `delegate` may name the caller it acts for in `X-Fortress-Caller`, the principal
    is then `<token>:<caller>`. Any other token sending that header is rejected.

    The response never says why a token was rejected, `AuthError.reason` only goes to the log.

    With `access`, a request carrying `Cf-Access-Jwt-Assertion` is authenticated by that signed
    assertion only, a bad one is rejected and never falls back to the bearer token. A request
    without the header needs a bearer token as before.

    Args:
    ----------
        app (ASGIApp):
            Wrapped application
        auth (TokenAuth):
            Token verifier
        log (LogStream):
            Audit log
        public_paths (frozenset[str]):
            Paths served without a token
        access (AccessAuth | None):
            Verifier of the Cloudflare Access assertion, None ignores the header

    """

    def __init__(
        self,
        app: ASGIApp,
        auth: TokenAuth,
        log: LogStream,
        public_paths: frozenset[str] = _PUBLIC_PATHS,
        access: AccessAuth | None = None,
    ) -> None:
        self._app = app
        self._auth = auth
        self._log = log
        self._public_paths = public_paths
        self._access = access

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] == "lifespan" or scope.get("path") in self._public_paths:
            await self._app(scope, receive, send)
            return

        _path: str = scope.get("path", "")
        _client = scope.get("client")
        _address: str = _client[0] if _client else "-"
        try:
            _principal: Principal = await self._authenticate(scope)
        except AuthError as e:
            self._log.warning(
                "auth rejected",
                metadata={
                    "reason": e.reason,
                    "path": _path,
                    "client": _address,
                },
            )
            _response = JsonResponse(
                content={"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await _response(scope, receive, send)
            return

        scope.setdefault("state", {})["principal"] = _principal
        await self._app(scope, receive, send)

    async def _authenticate(
        self,
        scope: Scope,
    ) -> Principal:
        _raw: str | None = None
        _caller: str | None = None
        _assertion: str | None = None
        for _key, _value in scope.get("headers", []):
            if _key == b"authorization" and _raw is None:
                _raw = _value.decode("latin-1")
            elif _key == _CALLER_HEADER:
                _caller = _value.decode("latin-1")
            elif _key == _ASSERTION_HEADER and _assertion is None:
                _assertion = _value.decode("latin-1")

        if self._access is not None and _assertion is not None:
            # Fetching the signing keys is a blocking call
            _principal: Principal = await run_in_threadpool(self._access.verify, _assertion)
        else:
            _principal = self._verify_bearer(_raw)
        return self._delegate(_principal, _caller)

    def _verify_bearer(
        self,
        raw: str | None,
    ) -> Principal:
        if raw is None:
            raise AuthError("missing")
        _scheme, _, _token = raw.partition(" ")
        if _scheme.lower() != "bearer":
            raise AuthError("malformed")
        return self._auth.verify(_token.strip())

    @staticmethod
    def _delegate(
        principal: Principal,
        caller: str | None,
    ) -> Principal:
        if caller is None:
            return principal

        if not principal.delegate:
            raise AuthError("delegation denied")
        if not _CALLER_PATTERN.match(caller):
            raise AuthError("malformed caller")
        _delegated: Principal = Principal(
            name=f"{principal.name}:{caller}",
            description=principal.description,
        )
        return _delegated
