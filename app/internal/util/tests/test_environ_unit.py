from __future__ import annotations

import os

from app.internal.util.environ import IEnviron


class TestIEnvironGetVariable:
    def test_get_existing_variable_returns_value(self, monkeypatch):
        monkeypatch.setenv("FORTRESS_TEST_VAR", "hello")
        result = IEnviron.get_variable("FORTRESS_TEST_VAR")
        assert result == "hello"

    def test_get_missing_variable_returns_none_by_default(self, monkeypatch):
        monkeypatch.delenv("FORTRESS_TEST_MISSING", raising=False)
        result = IEnviron.get_variable("FORTRESS_TEST_MISSING")
        assert result is None

    def test_get_missing_variable_returns_default(self, monkeypatch):
        monkeypatch.delenv("FORTRESS_TEST_MISSING", raising=False)
        result = IEnviron.get_variable("FORTRESS_TEST_MISSING", default="fallback")
        assert result == "fallback"

    def test_get_existing_variable_ignores_default(self, monkeypatch):
        monkeypatch.setenv("FORTRESS_TEST_VAR", "hello")
        result = IEnviron.get_variable("FORTRESS_TEST_VAR", default="fallback")
        assert result == "hello"

    def test_get_variable_with_none_name_returns_default(self):
        result = IEnviron.get_variable(None, default="fallback")
        assert result == "fallback"


class TestIEnvironSetVariable:
    def test_set_variable_creates_new_variable(self, monkeypatch):
        monkeypatch.delenv("FORTRESS_TEST_NEW", raising=False)
        IEnviron.set_variable("FORTRESS_TEST_NEW", "value")
        assert os.environ["FORTRESS_TEST_NEW"] == "value"

    def test_set_variable_overwrites_existing_variable(self, monkeypatch):
        monkeypatch.setenv("FORTRESS_TEST_VAR", "old")
        IEnviron.set_variable("FORTRESS_TEST_VAR", "new")
        assert os.environ["FORTRESS_TEST_VAR"] == "new"

    def test_set_then_get_round_trip(self, monkeypatch):
        monkeypatch.delenv("FORTRESS_TEST_ROUNDTRIP", raising=False)
        IEnviron.set_variable("FORTRESS_TEST_ROUNDTRIP", "value")
        assert IEnviron.get_variable("FORTRESS_TEST_ROUNDTRIP") == "value"
