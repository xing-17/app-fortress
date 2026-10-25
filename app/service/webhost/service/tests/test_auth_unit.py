from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.service._common.auth import Principal
from app.service._common.tests._assertions import make_key, mint
from app.service.webhost.service.auth import SessionStore, safe_next
from app.service.webhost.service.service import WebHostService
from app.setting.service import WebHostServiceSetting

from .conftest import HTML, JSON, make_setting


class TestLogin:
    def test_page_without_session_goes_to_login(self, web):
        _res = web.get("/n/centre?tab=x", headers=HTML)
        assert _res.status_code == 303
        assert _res.headers["location"] == "/login?next=%2Fn%2Fcentre%3Ftab%3Dx"

    def test_call_without_session_is_401(self, web):
        _res = web.get("/n/centre/d/src/alpha/runs/run_1", headers=JSON)
        assert _res.status_code == 401
        assert _res.json() == {"error": "unauthorized"}

    def test_login_page_is_public(self, web):
        _res = web.get("/login", headers=HTML)
        assert _res.status_code == 200
        assert 'type="password"' in _res.text

    @pytest.mark.parametrize("token", ["", "x" * 64, "short"])
    def test_wrong_token_is_rejected(self, web, token, log):
        _res = web.post("/login", data={"token": token})
        assert _res.status_code == 401
        assert "fortress_session" not in _res.cookies
        assert "Invalid token" in _res.text
        assert log.warning.called

    def test_good_token_opens_a_session(self, web, auth):
        _res = web.post("/login", data={"token": auth.token("me"), "next": "/n/centre"})
        assert _res.status_code == 303
        assert _res.headers["location"] == "/n/centre"
        _cookie = _res.headers["set-cookie"]
        assert "fortress_session=" in _cookie
        assert "HttpOnly" in _cookie
        assert "SameSite=lax" in _cookie
        assert web.get("/", headers=HTML).status_code == 200

    @pytest.mark.parametrize("target", ["//evil.example", "https://evil.example", "/\\evil", "evil"])
    def test_next_never_leaves_the_host(self, web, auth, target):
        _res = web.post("/login", data={"token": auth.token("me"), "next": target})
        assert _res.headers["location"] == "/"

    def test_logout_ends_the_session(self, signed_in):
        assert signed_in.post("/logout").status_code == 303
        assert signed_in.get("/", headers=HTML).status_code == 303


class TestGuards:
    def test_foreign_host_is_refused(self, web):
        assert web.get("/login", headers={"Host": "evil.example.org"}).status_code == 421

    def test_public_host_is_allowed(self, log, fake, auth):
        _service = WebHostService(
            make_setting(public_hosts=["console.example.org"]), clients={"centre": fake}, auth=auth
        )
        _service.start()
        with TestClient(_service.asgi_app(), base_url="http://console.example.org") as _web:
            assert _web.get("/login").status_code == 200
        _service.stop()

    def test_cross_origin_post_is_refused(self, signed_in):
        _res = signed_in.post(
            "/n/centre/query", json={"sql": "SELECT 1"}, headers={"Origin": "http://evil.example.org"}
        )
        assert _res.status_code == 403

    def test_same_origin_post_is_allowed(self, signed_in):
        _res = signed_in.post("/n/centre/query", json={"sql": "SELECT 1"}, headers={"Origin": "http://127.0.0.1:8802"})
        assert _res.status_code == 200

    def test_security_headers(self, web):
        _res = web.get("/login")
        assert "default-src 'self'" in _res.headers["content-security-policy"]
        assert _res.headers["x-content-type-options"] == "nosniff"
        assert _res.headers["cache-control"] == "no-store"

    def test_static_is_public_and_cacheable(self, web):
        _res = web.get("/static/app.css")
        assert _res.status_code == 200
        assert "cache-control" not in _res.headers or "no-store" not in _res.headers["cache-control"]


class TestAccess:
    def test_valid_assertion_signs_in(self, behind_access, signing_key):
        _res = behind_access.get("/", headers={**HTML, "Cf-Access-Jwt-Assertion": mint(signing_key)})
        assert _res.status_code == 200
        assert "me" in _res.text
        assert "sign out" not in _res.text

    def test_stranger_is_rejected(self, behind_access, signing_key):
        _headers = {**HTML, "Cf-Access-Jwt-Assertion": mint(signing_key, email="stranger@example.com")}
        assert behind_access.get("/", headers=_headers).status_code == 401

    def test_bad_signature_never_falls_back_to_login(self, behind_access, auth):
        _headers = {**HTML, "Cf-Access-Jwt-Assertion": mint(make_key())}
        assert behind_access.get("/", headers=_headers).status_code == 401

    def test_without_assertion_the_login_page_still_works(self, behind_access, auth):
        assert behind_access.get("/", headers=HTML).status_code == 303
        _res = behind_access.post("/login", data={"token": auth.token("me")})
        assert _res.status_code == 303


class TestSessionStore:
    def test_expired_session_is_gone(self):
        _store = SessionStore(ttl_seconds=0)
        _sid = _store.create(_principal())
        assert _store.get(_sid) is None

    def test_cap_drops_the_oldest(self):
        _store = SessionStore(max_sessions=2)
        _first = _store.create(_principal())
        _store.create(_principal())
        _store.create(_principal())
        assert _store.get(_first) is None

    def test_unknown_and_empty_ids(self):
        _store = SessionStore()
        assert _store.get("nope") is None
        assert _store.get(None) is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("/a?b=1", "/a?b=1"), (None, "/"), ("", "/"), ("//x", "/"), ("http://x", "/")],
    )
    def test_safe_next(self, value, expected):
        assert safe_next(value) == expected


class TestService:
    def test_asgi_app_needs_auth(self, log, fake):
        _service = WebHostService(make_setting(), clients={"centre": fake})
        _service.start()
        with pytest.raises(RuntimeError, match="no auth"):
            _service.asgi_app()
        _service.stop()

    def test_asgi_app_needs_a_running_service(self, log, auth):
        with pytest.raises(RuntimeError, match="not running"):
            WebHostService(make_setting(), auth=auth).asgi_app()

    def test_unknown_injected_client_raises(self, log, fake):
        with pytest.raises(ValueError, match="not in the setting"):
            WebHostService(make_setting(), clients={"other": fake})

    def test_start_does_not_need_the_nodes(self, log, auth):
        _service = WebHostService(make_setting(), auth=auth)
        _service.start()
        assert _service.is_running
        _service.stop()

    def test_stop_closes_only_its_own_clients(self, log, fake, auth):
        _setting = WebHostServiceSetting(nodes=[{"name": "centre", "endpoint": "http://centre:8800", "token": "t"}])
        _service = WebHostService(_setting, clients={"centre": fake}, auth=auth)
        _service.start()
        _service.stop()
        assert fake.closed is False


def _principal():
    return Principal(name="me")
