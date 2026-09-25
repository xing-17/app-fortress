from __future__ import annotations

from app.internal.util.prefix import IPrefix


class TestIPrefixResolve:
    def test_resolve_strips_trailing_slash(self):
        assert IPrefix.resolve("my/prefix/") == "my/prefix"

    def test_resolve_leaves_leading_slash(self):
        assert IPrefix.resolve("/my/prefix") == "/my/prefix"

    def test_resolve_none_returns_empty_string(self):
        assert IPrefix.resolve(None) == ""

    def test_resolve_empty_string_returns_empty_string(self):
        assert IPrefix.resolve("") == ""

    def test_resolve_without_trailing_slash_is_unchanged(self):
        assert IPrefix.resolve("my/prefix") == "my/prefix"
