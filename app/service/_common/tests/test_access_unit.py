from __future__ import annotations

import time
from unittest.mock import MagicMock

import jwt
import pytest
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.internal.logstream import LogStream
from app.service._common.access import AccessAuth
from app.service._common.auth import AuthError, Principal, TokenAuth
from app.service._common.http import BearerAuthMiddleware
from app.setting.service import AccessSetting, AuthSetting, McpHostServiceSetting

from ._assertions import (
    AUDIENCE,
    EMAIL,
    TEAM,
    StaticKeys,
    make_key,
    mint,
)

_USERS = [{"email": EMAIL, "name": "me"}]


def _setting(**overrides) -> AccessSetting:
    return AccessSetting(
        **{
            "team_domain": TEAM,
            "audience": AUDIENCE,
            "users": _USERS,
            **overrides,
        }
    )


@pytest.fixture(scope="module")
def key():
    return make_key()


@pytest.fixture
def access(key) -> AccessAuth:
    return AccessAuth(_setting(), keys=StaticKeys(key))


class TestAccessSetting:
    def test_defaults_to_none_on_the_host(self):
        assert McpHostServiceSetting().access is None

    def test_from_yaml(self, tmp_path):
        from app.setting.service import ServicesSetting

        _path = tmp_path / "services.yaml"
        _path.write_text(
            f"mcphost:\n  access:\n    team_domain: {TEAM}\n    audience: {AUDIENCE}\n"
            "    users:\n      - email: Me@Example.com\n        name: me\n",
            encoding="utf-8",
        )
        _access = ServicesSetting.from_yaml(_path).mcphost.access
        assert _access.users[0].email == "me@example.com"

    @pytest.mark.parametrize(
        "domain", ["", "example.com", "x.cloudflareaccess.com.evil.com", "https://x.cloudflareaccess.com"]
    )
    def test_invalid_team_domain_raises(self, domain):
        with pytest.raises(ValidationError):
            _setting(team_domain=domain)

    def test_short_audience_raises(self):
        with pytest.raises(ValidationError):
            _setting(audience="abc")

    def test_no_users_raises(self):
        with pytest.raises(ValidationError):
            _setting(users=[])

    @pytest.mark.parametrize(
        "user", [{"email": "nope", "name": "me"}, {"email": EMAIL, "name": "Me"}, {"email": EMAIL, "name": ""}]
    )
    def test_invalid_user_raises(self, user):
        with pytest.raises(ValidationError):
            _setting(users=[user])

    def test_duplicate_emails_raise(self):
        with pytest.raises(ValidationError, match="duplicate"):
            _setting(users=[{"email": EMAIL, "name": "a"}, {"email": EMAIL.upper(), "name": "b"}])


class TestVerify:
    def test_a_valid_assertion_gives_the_configured_name(self, access, key):
        assert access.verify(mint(key)) == Principal(name="me", description="Cloudflare Access")

    def test_the_email_is_compared_in_lowercase(self, access, key):
        assert access.verify(mint(key, email=EMAIL.upper())).name == "me"

    @pytest.mark.parametrize(
        "overrides, reason",
        [
            ({"exp": int(time.time()) - 600}, "ExpiredSignatureError"),
            ({"aud": ["b" * 64]}, "InvalidAudienceError"),
            ({"iss": "https://evil.cloudflareaccess.com"}, "InvalidIssuerError"),
            ({"exp": None}, "MissingRequiredClaimError"),
            ({"iat": None}, "MissingRequiredClaimError"),
            ({"aud": None}, "MissingRequiredClaimError"),
        ],
    )
    def test_bad_claims_are_rejected(self, access, key, overrides, reason):
        with pytest.raises(AuthError) as e:
            access.verify(mint(key, **overrides))
        assert reason in e.value.reason

    def test_a_signature_of_another_key_is_rejected(self, access):
        with pytest.raises(AuthError, match="invalid token"):
            access.verify(mint(make_key()))

    def test_a_tampered_payload_is_rejected(self, access, key):
        _head, _body, _sig = mint(key).split(".")
        _other = mint(key, email="other@example.com").split(".")[1]
        with pytest.raises(AuthError):
            access.verify(f"{_head}.{_other}.{_sig}")

    def test_an_unsigned_token_is_rejected(self, access):
        _now = int(time.time())
        _claims = {"iss": f"https://{TEAM}", "aud": [AUDIENCE], "email": EMAIL, "iat": _now, "exp": _now + 300}
        with pytest.raises(AuthError):
            access.verify(jwt.encode(_claims, None, algorithm="none"))

    def test_a_symmetric_token_is_rejected(self, access):
        # Signed with the public numbers as a shared secret
        _now = int(time.time())
        _claims = {"iss": f"https://{TEAM}", "aud": [AUDIENCE], "email": EMAIL, "iat": _now, "exp": _now + 300}
        with pytest.raises(AuthError):
            access.verify(jwt.encode(_claims, "secret" * 8, algorithm="HS256"))

    def test_garbage_is_rejected(self, access):
        with pytest.raises(AuthError):
            access.verify("not-a-jwt")

    def test_an_identity_not_in_the_list_is_rejected(self, access, key):
        with pytest.raises(AuthError) as e:
            access.verify(mint(key, email="stranger@example.com"))
        assert e.value.reason == "access identity not allowed"

    def test_an_assertion_without_email_is_rejected(self, access, key):
        # What a service token looks like
        with pytest.raises(AuthError) as e:
            access.verify(mint(key, email=None))
        assert e.value.reason == "access identity missing"

    def test_unreachable_keys_reject_the_request(self, key):
        _down = StaticKeys(key, error=jwt.PyJWKClientConnectionError("down"))
        with pytest.raises(AuthError) as e:
            AccessAuth(_setting(), keys=_down).verify(mint(key))
        assert e.value.reason == "access keys unavailable"

    def test_an_unknown_key_id_is_rejected(self, key):
        _unknown = StaticKeys(key, error=jwt.PyJWKClientError("no key"))
        with pytest.raises(AuthError):
            AccessAuth(_setting(), keys=_unknown).verify(mint(key))

    def test_the_rejection_never_quotes_the_token(self, access, key):
        _token = mint(key, aud=["b" * 64])
        with pytest.raises(AuthError) as e:
            access.verify(_token)
        assert _token not in e.value.reason and _token not in str(e.value)

    def test_the_default_key_source_is_the_team_key_set(self):
        _auth = AccessAuth(_setting())
        assert _auth._keys.uri == f"https://{TEAM}/cdn-cgi/access/certs"


def _app(access: AccessAuth | None, tmp_path) -> tuple[TestClient, TokenAuth, MagicMock]:
    _key = tmp_path / "t.key"
    _key.write_text("t" * 64 + "\n", encoding="utf-8")
    _key.chmod(0o600)
    _auth = TokenAuth(AuthSetting(masterfile=str(_key), tokens=[{"name": "phone"}, {"name": "host", "delegate": True}]))
    _log = MagicMock(spec=LogStream)

    async def _who(request):
        return PlainTextResponse(request.state.principal.name)

    _starlette = Starlette(routes=[Route("/mcp", _who, methods=["GET"])])
    _starlette.add_middleware(BearerAuthMiddleware, auth=_auth, log=_log, public_paths=frozenset(), access=access)
    return TestClient(_starlette), _auth, _log


class TestMiddleware:
    def test_a_valid_assertion_is_accepted(self, access, key, tmp_path):
        _client, _, _ = _app(access, tmp_path)
        _res = _client.get("/mcp", headers={"Cf-Access-Jwt-Assertion": mint(key)})
        assert (_res.status_code, _res.text) == (200, "me")

    def test_an_assertion_wins_over_an_opaque_bearer_token(self, access, key, tmp_path):
        # What ChatGPT sends: Access swaps its OAuth token for the assertion
        _client, _, _ = _app(access, tmp_path)
        _headers = {"Authorization": "Bearer oauth:opaque", "Cf-Access-Jwt-Assertion": mint(key)}
        assert _client.get("/mcp", headers=_headers).text == "me"

    def test_a_bad_assertion_never_falls_back_to_a_valid_bearer(self, access, tmp_path):
        _client, _auth, _ = _app(access, tmp_path)
        _headers = {"Authorization": f"Bearer {_auth.token('phone')}", "Cf-Access-Jwt-Assertion": mint(make_key())}
        _res = _client.get("/mcp", headers=_headers)
        assert (_res.status_code, _res.json()) == (401, {"error": "unauthorized"})

    def test_the_bearer_token_still_works_without_an_assertion(self, access, tmp_path):
        _client, _auth, _ = _app(access, tmp_path)
        assert _client.get("/mcp", headers={"Authorization": f"Bearer {_auth.token('phone')}"}).text == "phone"

    def test_no_credentials_get_401(self, access, tmp_path):
        _client, _, _ = _app(access, tmp_path)
        assert _client.get("/mcp").status_code == 401

    def test_the_assertion_header_is_ignored_when_access_is_not_set_up(self, key, tmp_path):
        _client, _, _ = _app(None, tmp_path)
        assert _client.get("/mcp", headers={"Cf-Access-Jwt-Assertion": mint(key)}).status_code == 401

    def test_an_access_identity_cannot_name_another_caller(self, access, key, tmp_path):
        _client, _, _ = _app(access, tmp_path)
        _headers = {"Cf-Access-Jwt-Assertion": mint(key), "X-Fortress-Caller": "someone"}
        assert _client.get("/mcp", headers=_headers).status_code == 401

    def test_the_rejection_is_logged_without_the_token(self, access, key, tmp_path):
        _client, _, _log = _app(access, tmp_path)
        _token = mint(key, aud=["b" * 64])
        _client.get("/mcp", headers={"Cf-Access-Jwt-Assertion": _token})
        _logged = str(_log.warning.call_args)
        assert "InvalidAudienceError" in _logged
        assert _token not in _logged
