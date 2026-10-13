from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.resource.source.tushare.session import TushareSession


class TestSessionValidation:
    def test_empty_key_is_rejected(self):
        with pytest.raises(ValidationError):
            TushareSession(key="", ttl_hours=1)

    @pytest.mark.parametrize("ttl", [0, -1])
    def test_non_positive_ttl_is_rejected(self, ttl):
        with pytest.raises(ValidationError):
            TushareSession(key="k", ttl_hours=ttl)


class TestSessionConnect:
    def test_not_connected_session_is_expired(self, session):
        assert session.is_expired() is True
        assert session.connect_at is None

    def test_api_connects_lazily_and_is_cached(self, session, api, monkeypatch):
        _count = {"n": 0}

        def _pro_api(*_a, **_k):
            _count["n"] += 1
            return api

        monkeypatch.setattr("app.resource.source.tushare.session.tushare.pro_api", _pro_api)
        assert session.api is api
        assert session.api is api
        assert _count["n"] == 1
        assert session.is_expired() is False

    def test_expire_at_is_ttl_minus_margin(self, session):
        session.connect()
        assert session.expire_at - session.connect_at == pytest.approx(3600 - 60)

    def test_expired_session_reconnects(self, session, monkeypatch):
        _count = {"n": 0}

        def _pro_api(*_a, **_k):
            _count["n"] += 1
            return object()

        monkeypatch.setattr("app.resource.source.tushare.session.tushare.pro_api", _pro_api)
        _ = session.api
        session._expire_at = 0.0
        _ = session.api
        assert _count["n"] == 2
