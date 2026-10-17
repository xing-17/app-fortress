from __future__ import annotations

from app.resource._client.web.headers import WebHeaders


class TestBuild:
    def test_returns_defaults_without_updates(self):
        _headers = WebHeaders.build()
        assert "User-Agent" in _headers
        assert _headers["Accept-Encoding"] == "gzip, deflate"

    def test_updates_add_new_headers(self):
        _headers = WebHeaders.build({"Referer": "https://example.com"})
        assert _headers["Referer"] == "https://example.com"
        assert "User-Agent" in _headers

    def test_updates_override_defaults(self):
        _headers = WebHeaders.build({"User-Agent": "custom"})
        assert _headers["User-Agent"] == "custom"

    def test_does_not_mutate_defaults(self):
        WebHeaders.build({"User-Agent": "custom", "X-Extra": "1"})
        _headers = WebHeaders.build()
        assert _headers["User-Agent"] != "custom"
        assert "X-Extra" not in _headers

    def test_returns_independent_copies(self):
        _first = WebHeaders.build()
        _first["X-Mutated"] = "1"
        assert "X-Mutated" not in WebHeaders.build()
