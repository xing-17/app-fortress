from __future__ import annotations

from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from app.service._common.auth import AuthError, Principal
from app.setting.service import AccessSetting


class SigningKeySource(Protocol):
    """Where the signing key of a token comes from, `PyJWKClient` or a stand-in"""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class AccessAuth:
    """
    Verify the assertion Cloudflare Access signs for each request it lets through

    Access puts who the caller is in the `Cf-Access-Jwt-Assertion` header as a JWT signed with the
    keys published by the team. A request is accepted when all of these hold: the signature is
    valid for one of those keys (RS256 only), the issuer is the team, the audience is the AUD tag
    of the application, it is neither expired nor missing a claim, and its `email` is one of
    `setting.users`.

    The signing keys are fetched on first use and cached, a key id not in the cache refreshes it.
    A fetch that fails rejects the request, so no keys never means open.

    Args:
    ----------
        setting (AccessSetting):
            Team domain, audience and the identities allowed in
        keys (SigningKeySource | None):
            Source of the signing keys, defaults to the team's published keys

    Methods:
    ----------
        verify(assertion) -> Principal:
            The principal behind an assertion, raises `AuthError` when it is not acceptable

    """

    # Seconds the cached key set is used before it is fetched again
    KEY_LIFESPAN = 3600

    # Seconds of clock difference between Cloudflare and this machine that are tolerated
    LEEWAY = 10
    FETCH_TIMEOUT = 5

    def __init__(
        self,
        setting: AccessSetting,
        keys: SigningKeySource | None = None,
    ) -> None:
        self._issuer: str = f"https://{setting.team_domain}"
        self._audience: str = setting.audience
        self._users: dict[str, str] = {u.email: u.name for u in setting.users}
        self._keys: SigningKeySource = keys or PyJWKClient(
            f"{self._issuer}/cdn-cgi/access/certs",
            cache_keys=True,
            lifespan=self.KEY_LIFESPAN,
            timeout=self.FETCH_TIMEOUT,
        )

    def verify(
        self,
        assertion: str,
    ) -> Principal:
        try:
            _key = self._keys.get_signing_key_from_jwt(assertion)
            _claims: dict[str, Any] = jwt.decode(
                assertion,
                _key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self.LEEWAY,
                options={"require": ["exp", "iat", "iss", "aud"]},
            )
        except jwt.PyJWKClientConnectionError as e:
            raise AuthError(f"access keys unavailable, reason: {e}") from e
        except jwt.PyJWTError as e:
            # The class name is enough for the log, the message may quote the token
            raise AuthError(f"access assertion {type(e).__name__}, reason: {e}") from e

        _email = _claims.get("email")
        if not isinstance(_email, str):
            # A service token carries no email
            raise AuthError("access identity missing")
        _name: str | None = self._users.get(_email.lower())
        if _name is None:
            raise AuthError("access identity not allowed")
        return Principal(name=_name, description="Cloudflare Access")
