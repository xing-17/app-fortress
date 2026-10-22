from __future__ import annotations

import os
import re
import stat
from datetime import date, timedelta

import pytest

from app.resource._global.setting import GlobalSetting
from app.service.node.service.auth import (
    AuthError,
    NodeAuth,
    Principal,
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
    monkeypatch.setattr(NodeAuth, "_today", lambda self: _DAY[0])


@pytest.fixture
def key_path(tmp_path):
    return _write_key(tmp_path / "master.key")


@pytest.fixture
def auth(key_path):
    return NodeAuth(_setting(key_path))


class TestMasterKey:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            NodeAuth(_setting(tmp_path / "nope.key"))

    def test_short_key_raises_without_leaking_it(self, tmp_path):
        _p = _write_key(tmp_path / "short.key", text="hunter2hunter2")
        with pytest.raises(ValueError, match="shorter") as e:
            NodeAuth(_setting(_p))
        assert "hunter2" not in str(e.value)

    @pytest.mark.skipif(os.name != "posix", reason="posix permissions")
    @pytest.mark.parametrize("mode", [0o644, 0o640, 0o604])
    def test_loose_permissions_raise(self, tmp_path, mode):
        _p = _write_key(tmp_path / "loose.key", mode=mode)
        with pytest.raises(PermissionError, match="chmod 600"):
            NodeAuth(_setting(_p))

    def test_relative_path_uses_base_dir(self, tmp_path):
        _sub = tmp_path / "settings"
        _sub.mkdir()
        _write_key(tmp_path / "master.key")
        _setting_rel = AuthSetting(masterfile="../master.key", tokens=[{"name": "a"}])
        _auth = NodeAuth(_setting_rel, base_dir=_sub)
        assert _auth.verify(_auth.token("a")).name == "a"

    def test_relative_path_defaults_to_cwd(self, tmp_path, monkeypatch):
        _write_key(tmp_path / "master.key")
        monkeypatch.chdir(tmp_path)
        _auth = NodeAuth(AuthSetting(masterfile="master.key", tokens=[{"name": "a"}]))
        assert _auth.verify(_auth.token("a")).name == "a"


class TestGenerateMasterFile:
    def test_creates_strong_private_file(self, tmp_path):
        _p = tmp_path / "dir" / "master.key"
        _setting_new = AuthSetting(masterfile=str(_p), tokens=[{"name": "a"}])
        assert NodeAuth.generate_master_file(_setting_new) == _p.resolve()
        assert len(_p.read_text().strip()) == 64
        if os.name == "posix":
            assert stat.S_IMODE(_p.stat().st_mode) == 0o600
        NodeAuth(_setting_new)

    def test_relative_path_uses_base_dir(self, tmp_path):
        _s = AuthSetting(masterfile="../auth/master.key")
        _sub = tmp_path / "settings"
        _sub.mkdir()
        assert NodeAuth.generate_master_file(_s, _sub) == (tmp_path / "auth" / "master.key").resolve()

    def test_existing_file_is_not_overwritten(self, key_path):
        _before = key_path.read_text()
        assert NodeAuth.generate_master_file(_setting(key_path)) is None
        assert key_path.read_text() == _before


class TestToken:
    def test_is_64_hex_without_name(self, auth):
        assert re.fullmatch(r"[0-9a-f]{64}", auth.token("mac-1"))

    def test_deterministic_across_instances(self, key_path):
        assert NodeAuth(_setting(key_path)).token("chatgpt") == NodeAuth(_setting(key_path)).token("chatgpt")

    def test_differs_per_name_version_and_key(self, tmp_path, key_path, auth):
        _other_key = _write_key(tmp_path / "other.key", text="z" * 64)
        _other = NodeAuth(_setting(_other_key))
        _bumped = NodeAuth(_setting(key_path, tokens=[{"name": "chatgpt", "version": 2}]))
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
        _auth = NodeAuth(_setting(key_path, tokens))
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
        _auth = NodeAuth(_setting(key_path, [{"name": "a", "expires": _TODAY.isoformat()}]))
        assert _auth.verify(_auth.token("a")).name == "a"

    def test_expired_after_last_day(self, key_path):
        _auth = NodeAuth(_setting(key_path, [{"name": "a", "expires": _TODAY.isoformat()}]))
        _raw = _auth.token("a")
        _DAY[0] = _TODAY + timedelta(days=1)
        with pytest.raises(AuthError) as e:
            _auth.verify(_raw)
        assert e.value.reason == "expired"

    def test_revoked(self, key_path):
        _raw = NodeAuth(_setting(key_path, [{"name": "a"}])).token("a")
        _dead = NodeAuth(_setting(key_path, [{"name": "a", "revoked": True}]))
        with pytest.raises(AuthError) as e:
            _dead.verify(_raw)
        assert e.value.reason == "revoked"

    def test_rotation_invalidates_old_token(self, key_path):
        _v1 = NodeAuth(_setting(key_path, [{"name": "a", "version": 1}]))
        _v2 = NodeAuth(_setting(key_path, [{"name": "a", "version": 2}]))
        _old = _v1.token("a")
        with pytest.raises(AuthError) as e:
            _v2.verify(_old)
        assert e.value.reason == "mismatch"
        assert _v2.verify(_v2.token("a")).name == "a"

    def test_removed_entry(self, key_path, auth):
        _raw = auth.token("mac-1")
        _gone = NodeAuth(_setting(key_path, [{"name": "chatgpt"}]))
        with pytest.raises(AuthError) as e:
            _gone.verify(_raw)
        assert e.value.reason == "mismatch"

    def test_token_from_another_master_key(self, tmp_path, auth):
        _k2 = _write_key(tmp_path / "k2.key", text="z" * 64)
        with pytest.raises(AuthError) as e:
            auth.verify(NodeAuth(_setting(_k2)).token("chatgpt"))
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
        _live = NodeAuth(_setting(key_path, [{"name": "a"}]))
        _dead = NodeAuth(_setting(key_path, [{"name": "a", "revoked": True}]))
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
