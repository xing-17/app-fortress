"""
综合测试：app.bridges.providers.base.session

覆盖范围
--------
- TestTTL        ttl_seconds / ttl_margin 解析与 ttl_interval 计算
- TestReadiness  is_ready() 在 connect 前后的状态
- TestExpiry     is_expired() 无 ttl / 有 ttl / 刚好到期
- TestConnect    connect() 更新 _session 与 _active_at
- TestClose      close() 清理状态并调用 _close_session
- TestRefresh    refresh() 创建新 session 并关闭旧 session
- TestGetSession get_session() 懒连接与过期自动刷新
- TestExport     export() 返回结构正确
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from app.bridges.providers.base.session import BaseSession

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _CountingSession(BaseSession):
    """每次 _create_session 返回递增整数，方便区分新旧 session 实例。"""

    def __init__(self, **kwargs: Any) -> None:
        self._counter = 0
        self._closed: list[Any] = []
        super().__init__(**kwargs)

    def _create_session(self) -> int:
        self._counter += 1
        return self._counter

    def _close_session(self, session: Any) -> None:
        self._closed.append(session)


def _make(ttl_seconds: int | None = None, ttl_margin: int | None = None) -> _CountingSession:
    return _CountingSession(
        name="test",
        type="mock",
        region="cn",
        ttl_seconds=ttl_seconds,
        ttl_margin=ttl_margin,
    )


_FIXED_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


# ──────────────────────────────────────────────────────────────────────────────
# TestTTL
# ──────────────────────────────────────────────────────────────────────────────


class TestTTL:
    def test_ttl_seconds_stored(self):
        s = _make(ttl_seconds=300)
        assert s.ttl_seconds == 300

    def test_ttl_seconds_none_when_not_provided(self):
        s = _make()
        assert s.ttl_seconds is None

    def test_ttl_seconds_zero_raises(self):
        with pytest.raises(ValueError):
            _make(ttl_seconds=0)

    def test_ttl_seconds_negative_raises(self):
        with pytest.raises(ValueError):
            _make(ttl_seconds=-10)

    def test_ttl_margin_stored(self):
        s = _make(ttl_seconds=300, ttl_margin=30)
        assert s.ttl_margin == 30

    def test_ttl_margin_zero_is_allowed(self):
        s = _make(ttl_seconds=300, ttl_margin=0)
        assert s.ttl_margin == 0

    def test_ttl_margin_negative_raises(self):
        with pytest.raises(ValueError):
            _make(ttl_seconds=300, ttl_margin=-1)

    def test_ttl_margin_equal_to_ttl_raises(self):
        with pytest.raises(ValueError):
            _make(ttl_seconds=300, ttl_margin=300)

    def test_ttl_margin_greater_than_ttl_raises(self):
        with pytest.raises(ValueError):
            _make(ttl_seconds=300, ttl_margin=400)

    def test_ttl_interval_equals_ttl_when_no_margin(self):
        s = _make(ttl_seconds=300)
        assert s.ttl_interval == 300

    def test_ttl_interval_subtracts_margin(self):
        s = _make(ttl_seconds=300, ttl_margin=30)
        assert s.ttl_interval == 270

    def test_ttl_interval_none_when_no_ttl(self):
        s = _make()
        assert s.ttl_interval is None


# ──────────────────────────────────────────────────────────────────────────────
# TestReadiness
# ──────────────────────────────────────────────────────────────────────────────


class TestReadiness:
    def test_not_ready_on_init(self):
        s = _make()
        assert not s.is_ready()

    def test_session_is_none_on_init(self):
        s = _make()
        assert s._session is None

    def test_active_at_is_none_on_init(self):
        s = _make()
        assert s.active_at is None

    def test_ready_after_connect(self):
        s = _make()
        s.connect()
        assert s.is_ready()

    def test_active_at_set_after_connect(self):
        s = _make()
        s.connect()
        assert isinstance(s.active_at, datetime)

    def test_not_ready_after_close(self):
        s = _make()
        s.connect()
        s.close()
        assert not s.is_ready()


# ──────────────────────────────────────────────────────────────────────────────
# TestExpiry
# ──────────────────────────────────────────────────────────────────────────────


class TestExpiry:
    def test_not_ready_session_counts_as_expired(self):
        s = _make(ttl_seconds=300)
        assert s.is_expired()

    def test_no_ttl_never_expires(self):
        s = _make()
        s.connect()
        assert not s.is_expired()

    def test_within_ttl_not_expired(self, monkeypatch):
        s = _make(ttl_seconds=300)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        assert not s.is_expired()

    def test_past_ttl_is_expired(self, monkeypatch):
        s = _make(ttl_seconds=300)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        future = _FIXED_DT + timedelta(seconds=301)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: future)
        assert s.is_expired()

    def test_exactly_at_ttl_boundary_is_expired(self, monkeypatch):
        s = _make(ttl_seconds=300)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        at_boundary = _FIXED_DT + timedelta(seconds=300)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: at_boundary)
        assert s.is_expired()

    def test_margin_reduces_effective_ttl(self, monkeypatch):
        s = _make(ttl_seconds=300, ttl_margin=60)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        # 241 seconds later — past ttl_interval (240) but before raw ttl (300)
        after_interval = _FIXED_DT + timedelta(seconds=241)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: after_interval)
        assert s.is_expired()


# ──────────────────────────────────────────────────────────────────────────────
# TestConnect
# ──────────────────────────────────────────────────────────────────────────────


class TestConnect:
    def test_connect_sets_session(self):
        s = _make()
        s.connect()
        assert s._session is not None

    def test_connect_sets_active_at(self):
        s = _make()
        s.connect()
        assert isinstance(s._active_at, datetime)

    def test_connect_returns_session_value(self):
        s = _make()
        result = s.connect()
        assert result == s._session

    def test_connect_calls_create_session_once(self):
        s = _make()
        s.connect()
        assert s._counter == 1

    def test_connect_active_at_matches_current_time(self, monkeypatch):
        s = _make()
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        assert s._active_at == _FIXED_DT


# ──────────────────────────────────────────────────────────────────────────────
# TestClose
# ──────────────────────────────────────────────────────────────────────────────


class TestClose:
    def test_close_clears_session(self):
        s = _make()
        s.connect()
        s.close()
        assert s._session is None

    def test_close_clears_active_at(self):
        s = _make()
        s.connect()
        s.close()
        assert s._active_at is None

    def test_close_calls_close_session_with_old_handle(self):
        s = _make()
        s.connect()
        handle = s._session
        s.close()
        assert handle in s._closed

    def test_close_on_disconnected_does_not_raise(self):
        s = _make()
        s.close()  # no-op, must not raise

    def test_close_twice_does_not_raise(self):
        s = _make()
        s.connect()
        s.close()
        s.close()


# ──────────────────────────────────────────────────────────────────────────────
# TestRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_creates_new_session(self):
        s = _make()
        s.connect()
        first = s._session
        s.refresh()
        assert s._session != first

    def test_refresh_closes_old_session(self):
        s = _make()
        s.connect()
        first = s._session
        s.refresh()
        assert first in s._closed

    def test_refresh_increments_counter(self):
        s = _make()
        s.connect()
        s.refresh()
        assert s._counter == 2

    def test_refresh_updates_active_at(self, monkeypatch):
        s = _make()
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        s.connect()
        later = _FIXED_DT + timedelta(seconds=10)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: later)
        s.refresh()
        assert s._active_at == later


# ──────────────────────────────────────────────────────────────────────────────
# TestGetSession
# ──────────────────────────────────────────────────────────────────────────────


class TestGetSession:
    def test_lazy_connect_on_first_call(self):
        s = _make()
        assert not s.is_ready()
        s.get_session()
        assert s.is_ready()

    def test_returns_same_handle_when_valid(self):
        s = _make(ttl_seconds=300)
        first = s.get_session()
        second = s.get_session()
        assert first == second

    def test_refreshes_when_expired(self, monkeypatch):
        s = _make(ttl_seconds=300)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: _FIXED_DT)
        first = s.get_session()
        future = _FIXED_DT + timedelta(seconds=301)
        monkeypatch.setattr(s, "_get_current_datetime", lambda: future)
        second = s.get_session()
        assert second != first

    def test_error_in_create_session_propagates(self):
        class _BrokenSession(BaseSession):
            def _create_session(self) -> Any:
                raise RuntimeError("connection refused")

        s = _BrokenSession(name="x", type="mock", region="cn")
        with pytest.raises(RuntimeError, match="connection refused"):
            s.get_session()


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_required_keys(self):
        s = _make()
        assert set(s.export()) == {"ttl_seconds", "ttl_margin", "ttl_interval", "active_at"}

    def test_export_active_at_none_before_connect(self):
        s = _make()
        assert s.export()["active_at"] is None

    def test_export_active_at_is_isoformat_after_connect(self):
        s = _make()
        s.connect()
        value = s.export()["active_at"]
        assert isinstance(value, str)
        datetime.fromisoformat(value)  # must not raise

    def test_export_ttl_values_match_init(self):
        s = _make(ttl_seconds=600, ttl_margin=60)
        result = s.export()
        assert result["ttl_seconds"] == 600
        assert result["ttl_margin"] == 60
        assert result["ttl_interval"] == 540

    def test_export_ttl_none_when_not_set(self):
        s = _make()
        result = s.export()
        assert result["ttl_seconds"] is None
        assert result["ttl_margin"] is None
        assert result["ttl_interval"] is None
