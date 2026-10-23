from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

TEAM = "team-x.cloudflareaccess.com"
AUDIENCE = "a" * 64
EMAIL = "me@example.com"


def make_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StaticKeys:
    """Signing key source with one public key, or none reachable when `error` is set"""

    def __init__(
        self,
        key: rsa.RSAPrivateKey,
        error: Exception | None = None,
    ) -> None:
        self._public = key.public_key()
        self._error = error

    def get_signing_key_from_jwt(self, token: str) -> Any:
        if self._error is not None:
            raise self._error
        return SimpleNamespace(key=self._public)


def mint(key: rsa.RSAPrivateKey, **overrides: Any) -> str:
    _now = int(time.time())
    _claims: dict[str, Any] = {
        "iss": f"https://{TEAM}",
        "aud": [AUDIENCE],
        "email": EMAIL,
        "iat": _now,
        "exp": _now + 300,
        "sub": "user-1",
    }
    _claims.update(overrides)
    _claims = {k: v for k, v in _claims.items() if v is not None}
    return jwt.encode(
        _claims,
        key,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
