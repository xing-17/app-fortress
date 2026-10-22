from __future__ import annotations

import pytest

from app.service.node.dra.errors import DRABusyError
from app.service.node.dra.pool import DRAPool


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Env:
    """Pool under test with a manual clock and a record of what it built and closed."""

    def __init__(self, **kwargs) -> None:
        self.now = 1000.0
        self.built: list[_FakeSession] = []
        self.closed_log: list[tuple[str, str]] = []
        self.fail = False
        kwargs.setdefault("max_sessions", 2)
        self.pool = DRAPool(
            factory=self._factory,
            clock=lambda: self.now,
            on_close=lambda key, reason: self.closed_log.append((key, reason)),
            **kwargs,
        )

    def _factory(self) -> _FakeSession:
        if self.fail:
            raise RuntimeError("build failed")
        _session = _FakeSession()
        self.built.append(_session)
        return _session

    def use(self, key: str) -> _FakeSession:
        with self.pool.lease(key) as _session:
            return _session


class TestInit:
    def test_max_sessions_must_be_positive(self):
        with pytest.raises(ValueError, match="at least 1"):
            DRAPool(factory=_FakeSession, max_sessions=0)


class TestLease:
    def test_builds_on_first_use_and_reuses(self):
        _env = _Env()
        assert _env.use("a") is _env.use("a")
        assert len(_env.built) == 1

    def test_keys_get_their_own_session(self):
        _env = _Env()
        assert _env.use("a") is not _env.use("b")

    def test_release_happens_when_the_body_raises(self):
        _env = _Env(max_sessions=1)
        with pytest.raises(KeyError):
            with _env.pool.lease("a"):
                raise KeyError("x")
        assert _env.pool.stats()["busy_sessions"] == 0

    def test_nested_lease_of_the_same_key_shares_the_session(self):
        _env = _Env(max_sessions=1)
        with _env.pool.lease("a") as _outer:
            with _env.pool.lease("a") as _inner:
                assert _inner is _outer
                assert _env.pool.stats()["busy_sessions"] == 1
        assert _env.pool.stats()["busy_sessions"] == 0


class TestEviction:
    def test_least_recently_used_is_evicted_and_closed(self):
        _env = _Env()
        _a = _env.use("a")
        _env.use("b")
        _env.use("c")
        assert _env.pool.keys() == ["b", "c"]
        assert _a.closed
        assert _env.closed_log == [("a", "lru")]

    def test_use_refreshes_the_rank(self):
        _env = _Env()
        _env.use("a")
        _env.use("b")
        _env.use("a")
        _env.use("c")
        assert _env.pool.keys() == ["a", "c"]

    def test_an_evicted_key_gets_a_new_session(self):
        _env = _Env(max_sessions=1)
        _first = _env.use("a")
        _env.use("b")
        assert _env.use("a") is not _first

    def test_busy_sessions_are_never_evicted(self):
        _env = _Env(max_sessions=1)
        with _env.pool.lease("a") as _a:
            with pytest.raises(DRABusyError):
                _env.use("b")
            assert not _a.closed
            assert _env.pool.keys() == ["a"]
        _env.use("b")
        assert _env.pool.keys() == ["b"]

    def test_a_busy_session_is_skipped_for_an_idle_one(self):
        _env = _Env()
        with _env.pool.lease("a"):
            _env.use("b")
            _env.use("c")
            assert _env.pool.keys() == ["a", "c"]

    def test_a_pool_of_one_serves_its_own_key_while_busy(self):
        _env = _Env(max_sessions=1)
        with _env.pool.lease("a") as _a:
            assert _env.use("a") is _a

    def test_a_failing_factory_keeps_the_healthy_session(self):
        _env = _Env(max_sessions=1)
        _a = _env.use("a")
        _env.fail = True
        with pytest.raises(RuntimeError, match="build failed"):
            _env.use("b")
        assert _env.pool.keys() == ["a"]
        assert not _a.closed


class TestIdle:
    def test_idle_sessions_are_closed_on_the_next_lease(self):
        _env = _Env(max_idle_seconds=60)
        _a = _env.use("a")
        _env.now += 61
        _env.use("b")
        assert _env.pool.keys() == ["b"]
        assert _a.closed
        assert _env.closed_log == [("a", "idle")]

    def test_not_yet_idle_enough_is_kept(self):
        _env = _Env(max_idle_seconds=60)
        _env.use("a")
        _env.now += 60
        _env.use("b")
        assert _env.pool.keys() == ["a", "b"]

    def test_release_restarts_the_idle_clock(self):
        _env = _Env(max_idle_seconds=60)
        with _env.pool.lease("a"):
            _env.now += 100
        _env.now += 30
        _env.use("b")
        assert _env.pool.keys() == ["a", "b"]

    def test_a_busy_session_is_not_expired(self):
        _env = _Env(max_idle_seconds=60)
        with _env.pool.lease("a"):
            _env.now += 61
            _env.use("b")
            assert "a" in _env.pool.keys()

    def test_zero_disables_expiry(self):
        _env = _Env(max_idle_seconds=0)
        _env.use("a")
        _env.now += 10**6
        _env.use("b")
        assert _env.pool.keys() == ["a", "b"]


class TestReset:
    def test_idle_sessions_are_closed(self):
        _env = _Env()
        _a = _env.use("a")
        _env.pool.reset()
        assert _a.closed
        assert _env.pool.keys() == []

    def test_a_busy_session_is_closed_when_released(self):
        _env = _Env()
        with _env.pool.lease("a") as _a:
            _env.pool.reset()
            assert _env.pool.keys() == []
            assert not _a.closed
        assert _a.closed

    def test_a_retired_session_is_closed_by_the_last_user(self):
        _env = _Env()
        with _env.pool.lease("a") as _a:
            with _env.pool.lease("a"):
                _env.pool.reset()
            assert not _a.closed
        assert _a.closed

    def test_the_key_gets_a_new_session_after_reset(self):
        _env = _Env()
        _first = _env.use("a")
        _env.pool.reset()
        assert _env.use("a") is not _first


class TestIntrospection:
    def test_stats(self):
        _env = _Env()
        _env.use("a")
        with _env.pool.lease("b"):
            assert _env.pool.stats() == {"sessions": 2, "busy_sessions": 1}

    def test_session_of_an_unknown_key_is_none(self):
        assert _Env().pool.session("a") is None
