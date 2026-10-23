from __future__ import annotations

import json
import os
import re
import stat
import threading
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.internal.logstream import LogStream
from app.resource._global.setting import GlobalSetting
from app.service._common import auth as auth_module
from app.service._common.auth import (
    AuthError,
    Principal,
    TokenAuth,
)
from app.setting.service import AuthSetting

_TODAY = date(2026, 10, 22)
_KEY = "k" * 64
_DAY = [_TODAY]


def _write_key(path, text=_KEY, mode=0o600):
    path.write_text(text + "\n", encoding="utf-8")
    path.chmod(mode)
    return path


def _setting(key_path, tokens=None):
    return AuthSetting(
        masterfile=str(key_path),
        tokens=tokens
        if tokens is not None
        else [
            {"name": "chatgpt", "description": "mcp", "version": 1, "expires": "2027-10-22"},
            {"name": "mac-1", "version": 2},
        ],
    )


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch):
    _DAY[0] = _TODAY
    monkeypatch.setattr(TokenAuth, "_today", lambda self: _DAY[0])


@pytest.fixture
def key_path(tmp_path):
    return _write_key(tmp_path / "master.key")


@pytest.fixture
def auth(key_path):
    return TokenAuth(_setting(key_path))


class TestMasterKey:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TokenAuth(_setting(tmp_path / "nope.key"))

    def test_short_key_raises_without_leaking_it(self, tmp_path):
        _p = _write_key(tmp_path / "short.key", text="hunter2hunter2")
        with pytest.raises(ValueError, match="shorter") as e:
            TokenAuth(_setting(_p))
        assert "hunter2" not in str(e.value)

    @pytest.mark.skipif(os.name != "posix", reason="posix permissions")
    @pytest.mark.parametrize("mode", [0o644, 0o640, 0o604])
    def test_loose_permissions_raise(self, tmp_path, mode):
        _p = _write_key(tmp_path / "loose.key", mode=mode)
        with pytest.raises(PermissionError, match="chmod 600"):
            TokenAuth(_setting(_p))

    def test_relative_path_uses_base_dir(self, tmp_path):
        _sub = tmp_path / "settings"
        _sub.mkdir()
        _write_key(tmp_path / "master.key")
        _setting_rel = AuthSetting(masterfile="../master.key", tokens=[{"name": "a"}])
        _auth = TokenAuth(_setting_rel, base_dir=_sub)
        assert _auth.verify(_auth.token("a")).name == "a"

    def test_relative_path_defaults_to_cwd(self, tmp_path, monkeypatch):
        _write_key(tmp_path / "master.key")
        monkeypatch.chdir(tmp_path)
        _auth = TokenAuth(AuthSetting(masterfile="master.key", tokens=[{"name": "a"}]))
        assert _auth.verify(_auth.token("a")).name == "a"


class TestGenerateMasterFile:
    def test_creates_strong_private_file(self, tmp_path):
        _p = tmp_path / "dir" / "master.key"
        _setting_new = AuthSetting(masterfile=str(_p), tokens=[{"name": "a"}])
        assert TokenAuth.generate_master_file(_setting_new) == _p.resolve()
        assert len(_p.read_text().strip()) == 64
        if os.name == "posix":
            assert stat.S_IMODE(_p.stat().st_mode) == 0o600
        TokenAuth(_setting_new)

    def test_relative_path_uses_base_dir(self, tmp_path):
        _s = AuthSetting(masterfile="../auth/master.key")
        _sub = tmp_path / "settings"
        _sub.mkdir()
        assert TokenAuth.generate_master_file(_s, _sub) == (tmp_path / "auth" / "master.key").resolve()

    def test_existing_file_is_not_overwritten(self, key_path):
        _before = key_path.read_text()
        assert TokenAuth.generate_master_file(_setting(key_path)) is None
        assert key_path.read_text() == _before


class TestToken:
    def test_is_64_hex_without_name(self, auth):
        assert re.fullmatch(r"[0-9a-f]{64}", auth.token("mac-1"))

    def test_deterministic_across_instances(self, key_path):
        assert TokenAuth(_setting(key_path)).token("chatgpt") == TokenAuth(_setting(key_path)).token("chatgpt")

    def test_differs_per_name_version_and_key(self, tmp_path, key_path, auth):
        _other_key = _write_key(tmp_path / "other.key", text="z" * 64)
        _other = TokenAuth(_setting(_other_key))
        _bumped = TokenAuth(_setting(key_path, tokens=[{"name": "chatgpt", "version": 2}]))
        _t = auth.token("chatgpt")
        assert _t != auth.token("mac-1")
        assert _t != _other.token("chatgpt")
        assert _t != _bumped.token("chatgpt")

    def test_unknown_name_raises(self, auth):
        with pytest.raises(ValueError, match="unknown"):
            auth.token("nope")

    @pytest.mark.parametrize(
        "tokens, state",
        [
            ([{"name": "a", "revoked": True}], "revoked"),
            ([{"name": "a", "expires": "2026-10-21"}], "expired"),
        ],
    )
    def test_inactive_token_cannot_be_shown(self, key_path, tokens, state):
        _auth = TokenAuth(_setting(key_path, tokens))
        assert _auth.state("a") == state
        with pytest.raises(ValueError, match=state):
            _auth.token("a")


class TestVerify:
    def test_valid_token(self, auth):
        assert auth.verify(auth.token("chatgpt")) == Principal(name="chatgpt", description="mcp")

    def test_each_entry_resolves_to_itself(self, auth):
        assert auth.verify(auth.token("chatgpt")).name == "chatgpt"
        assert auth.verify(auth.token("mac-1")).name == "mac-1"

    def test_last_day_is_still_valid(self, key_path):
        _auth = TokenAuth(_setting(key_path, [{"name": "a", "expires": _TODAY.isoformat()}]))
        assert _auth.verify(_auth.token("a")).name == "a"

    def test_expired_after_last_day(self, key_path):
        _auth = TokenAuth(_setting(key_path, [{"name": "a", "expires": _TODAY.isoformat()}]))
        _raw = _auth.token("a")
        _DAY[0] = _TODAY + timedelta(days=1)
        with pytest.raises(AuthError) as e:
            _auth.verify(_raw)
        assert e.value.reason == "expired"

    def test_revoked(self, key_path):
        _raw = TokenAuth(_setting(key_path, [{"name": "a"}])).token("a")
        _dead = TokenAuth(_setting(key_path, [{"name": "a", "revoked": True}]))
        with pytest.raises(AuthError) as e:
            _dead.verify(_raw)
        assert e.value.reason == "revoked"

    def test_rotation_invalidates_old_token(self, key_path):
        _v1 = TokenAuth(_setting(key_path, [{"name": "a", "version": 1}]))
        _v2 = TokenAuth(_setting(key_path, [{"name": "a", "version": 2}]))
        _old = _v1.token("a")
        with pytest.raises(AuthError) as e:
            _v2.verify(_old)
        assert e.value.reason == "mismatch"
        assert _v2.verify(_v2.token("a")).name == "a"

    def test_removed_entry(self, key_path, auth):
        _raw = auth.token("mac-1")
        _gone = TokenAuth(_setting(key_path, [{"name": "chatgpt"}]))
        with pytest.raises(AuthError) as e:
            _gone.verify(_raw)
        assert e.value.reason == "mismatch"

    def test_token_from_another_master_key(self, tmp_path, auth):
        _k2 = _write_key(tmp_path / "k2.key", text="z" * 64)
        with pytest.raises(AuthError) as e:
            auth.verify(TokenAuth(_setting(_k2)).token("chatgpt"))
        assert e.value.reason == "mismatch"

    def test_tampered_token(self, auth):
        _raw = auth.token("chatgpt")
        _bad = _raw[:-1] + ("0" if _raw[-1] != "0" else "1")
        with pytest.raises(AuthError) as e:
            auth.verify(_bad)
        assert e.value.reason == "mismatch"

    @pytest.mark.parametrize("raw", ["", "abc", "0" * 63, "0" * 65, "a" * 500, None, 123, b"0" * 64])
    def test_malformed_is_rejected(self, auth, raw):
        with pytest.raises(AuthError) as e:
            auth.verify(raw)
        assert e.value.reason == "malformed"

    @pytest.mark.parametrize("raw", ["0" * 64, "é" * 64])
    def test_wrong_but_well_sized_is_mismatch(self, auth, raw):
        with pytest.raises(AuthError) as e:
            auth.verify(raw)
        assert e.value.reason == "mismatch"

    def test_error_message_is_uniform(self, key_path):
        _live = TokenAuth(_setting(key_path, [{"name": "a"}]))
        _dead = TokenAuth(_setting(key_path, [{"name": "a", "revoked": True}]))
        _msgs = set()
        for _fn, _raw in [
            (_live.verify, "junk"),
            (_live.verify, "0" * 64),
            (_dead.verify, _live.token("a")),
        ]:
            with pytest.raises(AuthError) as e:
                _fn(_raw)
            _msgs.add(str(e.value))
        assert _msgs == {"invalid token"}

    def test_repr_does_not_leak_key(self, auth):
        assert _KEY not in repr(auth)


class TestCli:
    @pytest.fixture(autouse=True)
    def _reset_global_setting(self):
        GlobalSetting.reset()
        yield
        GlobalSetting.reset()

    def _write_settings(self, tmp_path):
        _dir = tmp_path / "settings"
        _dir.mkdir()
        (_dir / "system.yaml").write_text(
            "alias: t\nnode: snt\nversion: 0.0.1\ntimezone: UTC\n",
            encoding="utf-8",
        )
        (_dir / "services.yaml").write_text(
            "node:\n"
            "  auth:\n"
            "    masterfile: ../auth/master.key\n"
            "    tokens:\n"
            "      - name: chatgpt\n"
            "        description: mcp\n"
            "      - name: old\n"
            "        revoked: true\n",
            encoding="utf-8",
        )
        return _dir

    def _auth_for(self, tmp_path, service="node"):
        from app.cline import _build_auth

        _dir = self._write_settings(tmp_path)
        GlobalSetting.load(_dir)
        _services = GlobalSetting.get_services()
        _setting = getattr(_services, service).auth
        TokenAuth.generate_master_file(_setting, _dir)
        return _dir, _build_auth(service, _setting, _dir)

    def test_start_auth_follows_services_yaml(self, tmp_path):
        _dir, _auth = self._auth_for(tmp_path)
        assert _auth.hot_reload is True
        assert _auth.state("chatgpt") == "active"
        _file = _dir / "services.yaml"
        _file.write_text(
            "node:\n  auth:\n    masterfile: ../auth/master.key\n    tokens:\n"
            "      - name: chatgpt\n        revoked: true\n",
            encoding="utf-8",
        )
        os.utime(_file, ns=(2_000_000_000_000_000_000, 2_000_000_000_000_000_000))
        _auth._next_check = 0.0
        assert _auth.state("chatgpt") == "revoked"

    def test_start_auth_without_services_file_does_not_watch(self, tmp_path):
        from app.cline import _build_auth

        _dir = tmp_path / "settings"
        _dir.mkdir()
        (_dir / "system.yaml").write_text("alias: t\nnode: snt\nversion: 0.0.1\ntimezone: UTC\n", encoding="utf-8")
        GlobalSetting.load(_dir)
        _setting = AuthSetting(masterfile="../auth/master.key", tokens=[{"name": "a"}])
        TokenAuth.generate_master_file(_setting, _dir)
        assert _build_auth("node", _setting, _dir).hot_reload is False


class TestHotReload:
    @pytest.fixture
    def log(self):
        return MagicMock(spec=LogStream)

    @pytest.fixture
    def conf(self, tmp_path, key_path):
        _path = tmp_path / "auth.yaml"
        self._ticks = 0
        self._key_path = key_path
        self._write_conf(_path, [{"name": "a"}])
        return _path

    def _bump(self, path):
        # Force a new mtime, two writes in one tick must still read as a change
        self._ticks += 1
        _ns = 1_000_000_000_000_000_000 + self._ticks * 1_000_000_000
        os.utime(path, ns=(_ns, _ns))

    def _write_conf(self, path, tokens, masterfile=None):
        _body = {"masterfile": str(masterfile or self._key_path), "tokens": tokens}
        path.write_text(json.dumps(_body), encoding="utf-8")
        self._bump(path)

    def _load(self, path):
        return AuthSetting.from_yaml(path)

    @pytest.fixture
    def hot(self, conf, log):
        return TokenAuth(
            self._load(conf),
            reload=lambda: self._load(conf),
            watch=[conf],
            reload_interval=0,
            log=log,
        )

    def test_flag(self, hot, key_path):
        assert hot.hot_reload is True
        assert TokenAuth(_setting(key_path)).hot_reload is False

    def test_revoke_takes_effect(self, hot, conf):
        _raw = hot.token("a")
        assert hot.verify(_raw).name == "a"
        self._write_conf(conf, [{"name": "a", "revoked": True}])
        with pytest.raises(AuthError) as e:
            hot.verify(_raw)
        assert e.value.reason == "revoked"
        assert hot.state("a") == "revoked"

    def test_new_entry_takes_effect(self, hot, conf):
        with pytest.raises(ValueError, match="unknown"):
            hot.token("b")
        self._write_conf(conf, [{"name": "a"}, {"name": "b", "delegate": True}])
        _principal = hot.verify(hot.token("b"))
        assert _principal.name == "b"
        assert _principal.delegate is True
        assert [t.name for t in hot.setting.tokens] == ["a", "b"]

    def test_removed_entry_is_rejected(self, hot, conf):
        _raw = hot.token("a")
        self._write_conf(conf, [{"name": "b"}])
        with pytest.raises(AuthError) as e:
            hot.verify(_raw)
        assert e.value.reason == "mismatch"

    def test_version_bump_rotates(self, hot, conf):
        _old = hot.token("a")
        self._write_conf(conf, [{"name": "a", "version": 2}])
        with pytest.raises(AuthError):
            hot.verify(_old)
        assert hot.verify(hot.token("a")).name == "a"

    def test_masterkey_change_takes_effect(self, hot, tmp_path):
        _old = hot.token("a")
        _write_key(self._key_path, text="z" * 64)
        self._bump(self._key_path)
        with pytest.raises(AuthError) as e:
            hot.verify(_old)
        assert e.value.reason == "mismatch"
        assert hot.verify(hot.token("a")).name == "a"

    def test_masterfile_moved_by_the_setting(self, hot, conf, tmp_path):
        _old = hot.token("a")
        _moved = _write_key(tmp_path / "moved.key", text="m" * 64)
        self._write_conf(conf, [{"name": "a"}], masterfile=_moved)
        with pytest.raises(AuthError):
            hot.verify(_old)
        # The new file is watched from now on
        _write_key(_moved, text="n" * 64)
        self._bump(_moved)
        _expected = TokenAuth(AuthSetting(masterfile=str(_moved), tokens=[{"name": "a"}])).token("a")
        assert hot.token("a") == _expected

    def test_unchanged_files_do_not_reload(self, conf, log):
        _calls = []

        def _reload():
            _calls.append(1)
            return self._load(conf)

        _auth = TokenAuth(self._load(conf), reload=_reload, watch=[conf], reload_interval=0, log=log)
        for _ in range(5):
            _auth.verify(_auth.token("a"))
        assert _calls == []

    def test_interval_throttles_the_check(self, conf, log, monkeypatch):
        _now = [100.0]
        monkeypatch.setattr(auth_module.time, "monotonic", lambda: _now[0])
        _auth = TokenAuth(
            self._load(conf),
            reload=lambda: self._load(conf),
            watch=[conf],
            reload_interval=5,
            log=log,
        )
        # The first call is a check, the next one is allowed 5 s later
        assert _auth.state("a") == "active"
        self._write_conf(conf, [{"name": "a", "revoked": True}])
        _now[0] += 1
        assert _auth.state("a") == "active"
        _now[0] += 4
        assert _auth.state("a") == "revoked"

    def test_without_reload_files_are_ignored(self, conf, key_path):
        _auth = TokenAuth(self._load(conf))
        self._write_conf(conf, [{"name": "a", "revoked": True}])
        assert _auth.state("a") == "active"

    @pytest.mark.parametrize(
        "broken",
        [
            pytest.param("key: [unbalanced\n", id="yaml"),
            pytest.param('{"masterfile": "x", "tokens": [{"name": "Bad Name"}]}', id="schema"),
            pytest.param('{"masterfile": "/nope/none.key", "tokens": [{"name": "a"}]}', id="masterfile"),
            pytest.param('{"tokens": [{"name": "a"}, {"name": "a"}]}', id="duplicate"),
        ],
    )
    def test_failed_reload_keeps_the_previous_setting(self, hot, conf, log, broken):
        _raw = hot.token("a")
        conf.write_text(broken, encoding="utf-8")
        self._bump(conf)
        assert hot.verify(_raw).name == "a"
        log.error.assert_called_once()
        assert log.error.call_args.args[0].startswith("auth reload failed")

    def test_recovers_once_the_file_is_fixed(self, hot, conf, log):
        conf.write_text("key: [unbalanced\n", encoding="utf-8")
        self._bump(conf)
        hot.state("a")
        self._write_conf(conf, [{"name": "a", "revoked": True}])
        assert hot.state("a") == "revoked"
        log.info.assert_called_once()

    def test_failed_reload_is_not_retried_until_the_file_changes(self, conf, log):
        _calls = []

        def _reload():
            _calls.append(1)
            raise ValueError("bad")

        _auth = TokenAuth(self._load(conf), reload=_reload, watch=[conf], reload_interval=0, log=log)
        self._write_conf(conf, [{"name": "a", "version": 2}])
        for _ in range(4):
            _auth.state("a")
        assert len(_calls) == 1
        self._write_conf(conf, [{"name": "a", "version": 3}])
        _auth.state("a")
        assert len(_calls) == 2

    def test_loose_masterkey_permissions_keep_the_previous_key(self, hot, log):
        _raw = hot.token("a")
        self._key_path.write_text("z" * 64 + "\n", encoding="utf-8")
        self._key_path.chmod(0o644)
        self._bump(self._key_path)
        if os.name == "posix":
            assert hot.verify(_raw).name == "a"
            log.error.assert_called_once()

    def test_log_never_carries_a_key_or_token(self, hot, conf, log):
        _raw = hot.token("a")
        _write_key(self._key_path, text="short")
        self._bump(self._key_path)
        hot.state("a")
        self._write_conf(conf, [{"name": "a", "version": 2}])
        hot.state("a")
        _seen = repr(log.mock_calls)
        assert _KEY not in _seen
        assert _raw not in _seen
        assert "short" not in _seen.replace("shorter", "")

    def test_missing_file_at_start_still_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TokenAuth(
                AuthSetting(masterfile=str(tmp_path / "nope.key"), tokens=[{"name": "a"}]),
                reload=lambda: AuthSetting(),
            )

    def test_readers_never_see_a_torn_state_while_reloading(self, hot, conf):
        _stop = threading.Event()
        _errors: list[BaseException] = []

        def _read():
            _raw = hot.token("a")
            while not _stop.is_set():
                try:
                    hot.verify(_raw)
                except AuthError:
                    # Version flips make the old token mismatch, nothing else may happen
                    _raw = hot.token("a")
                except BaseException as e:
                    _errors.append(e)
                    return

        _threads = [threading.Thread(target=_read) for _ in range(4)]
        for _t in _threads:
            _t.start()
        try:
            for _v in range(2, 40):
                self._write_conf(conf, [{"name": "a", "version": _v}])
        finally:
            _stop.set()
            for _t in _threads:
                _t.join(timeout=5)
        assert _errors == []
