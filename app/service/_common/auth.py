from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.logstream import LogStream
from app.internal.util.clock import IClock
from app.setting.service import AuthSetting, TokenSetting

# (mtime_ns, size) of a file
# None when it cannot be stat-ed
_FileStamp = tuple[int, int] | None


class AuthError(Exception):
    """
    Token rejected, the message is the same for every cause so a caller learns nothing from it

    Attributes:
    ----------
        reason (str):
            Why it was rejected, for the audit log only: malformed, mismatch, revoked, expired

    """

    def __init__(
        self,
        reason: str,
    ) -> None:
        super().__init__("invalid token")
        self.reason = reason


class Principal(IAbstractDomain):
    """
    The caller behind a verified token

    Attributes:
    ----------
        name (str):
            Token name
        description (str):
            What the token is for
        delegate (bool):
            Whether the token may act for a caller named in the `X-Fortress-Caller` header

    """

    model_config = ConfigDict(frozen=True)  # immutable

    name: str = Field(
        ...,
        description="[Required] Token name",
    )
    description: str = Field(
        default="",
        description="[Optional] What the token is for",
    )
    delegate: bool = Field(
        default=False,
        description="[Optional] Whether the token may act for another caller",
    )


class TokenAuthState(IAbstractDomain):
    """
    Token Auth state used for keeping track of the current authentication setting

    Attributes:
    ----------
        setting (AuthSetting):
            The current authentication setting
        masterfile (Path):
            Path to the master key file
        masterkey (bytes):
            The master key used for deriving tokens
        entries (dict[str, TokenSetting]):
            Token entries keyed by their names
        stamps (dict[Path, _FileStamp]):
            File stamps for watched files

    """

    model_config = ConfigDict(frozen=True)  # immutable

    setting: AuthSetting = Field(
        ...,
        description="[Required] The current authentication setting",
    )
    masterfile: Path = Field(
        ...,
        description="[Required] Path to the master key file",
    )
    masterkey: bytes = Field(
        ...,
        description="[Required] The master key used for deriving tokens",
        repr=False,
    )
    entries: dict[str, TokenSetting] = Field(
        ...,
        description="[Required] Token entries keyed by their names",
    )
    stamps: dict[Path, _FileStamp] = Field(
        ...,
        description="[Required] File stamps for watched files",
    )


class TokenAuth:
    """
    Bearer token auth, tokens are derived from a master key and never stored

    token = <hex(HMAC-SHA256(master_key, "fortress-token-v1:<name>:<version>"))>

    Bump `version` of an entry to rotate its token, set `revoked` or remove the entry to kill it.

    With `reload`, the entries and the master key follow their files: when the master key file or
    a `watch` file changes, `reload` is called for the new setting and the master key is read
    again, so a revoke or a rotation needs no restart. A reload that fails (bad YAML, bad key) is
    logged and the previous setting stays in force. A typo never locks everybody out, but it does
    not revoke anything either, so watch the log.

    Args:
    ----------
        setting (AuthSetting):
            Auth setting with the master key file and the token entries
        base_dir (Path | None):
            Base of a relative masterfile, the settings directory, defaults to the working directory
        reload (Callable[[], AuthSetting] | None):
            Reads the auth setting again, None turns hot reload off
        watch (Sequence[Path]):
            Files that `reload` reads, the master key file is always watched
        reload_interval (float):
            Min seconds between two checks of the files, 0 checks on every call
        log (LogStream | None):
            Where reloads are logged, defaults to a stream named `auth`

    Attributes:
    ----------
        setting (AuthSetting):
            The setting in force
        hot_reload (bool):
            Whether the files are watched

    Methods:
    ----------
        token(name) -> str:
            Derive the token of an active entry
        verify(raw) -> Principal:
            Check a bearer token, raises AuthError when rejected
        state(name) -> str:
            "active", "revoked" or "expired"
        generate_master_file(setting, base_dir) -> Path | None:
            Create the master key file, None when it already exists

    """

    _min_masterkey_length = 32
    _domain_name: str = "fortress-token-v1"

    def __init__(
        self,
        setting: AuthSetting,
        base_dir: Path | None = None,
        reload: Callable[[], AuthSetting] | None = None,
        watch: Sequence[Path] = (),
        reload_interval: float = 1.0,
        log: LogStream | None = None,
    ) -> None:
        self._base_dir = base_dir
        self._reload = reload
        self._watch: tuple[Path, ...] = tuple(Path(p).resolve() for p in watch)
        self._reload_interval = reload_interval
        self._log: LogStream | None = log
        if reload is not None and log is None:
            self._log = LogStream(
                name="auth",
                tags={"service": "auth"},
            )
        self._reload_lock = threading.Lock()
        self._next_check: float = 0.0

        # Build the initial token authentication states
        self._state: TokenAuthState = self._build(setting)

    @property
    def setting(self) -> AuthSetting:
        return self._state.setting

    @property
    def hot_reload(self) -> bool:
        return self._reload is not None

    def _build(
        self,
        setting: AuthSetting,
    ) -> TokenAuthState:
        # Build auth state from the given setting
        _masterfile = self._resolve_masterfile(setting, self._base_dir)
        # Stamped before reading
        # a write during the read shows as a change on the next check
        _stamps = self._stamp((_masterfile, *self._watch))
        _entries: dict[str, TokenSetting] = {t.name: t for t in setting.tokens}
        _state: TokenAuthState = TokenAuthState(
            setting=setting,
            masterfile=_masterfile,
            masterkey=self._read_masterkey(_masterfile),
            entries=_entries,
            stamps=_stamps,
        )
        return _state

    @staticmethod
    def _stamp(paths: Sequence[Path]) -> dict[Path, _FileStamp]:
        _res: dict[Path, _FileStamp] = {}
        for _path in paths:
            try:
                _st = _path.stat()
                _res[_path] = (_st.st_mtime_ns, _st.st_size)
            except OSError:
                _res[_path] = None
        return _res

    def _current(self) -> TokenAuthState:
        # if reload not enabled, always return the current state
        # if now < next_check, return the current state
        # if fail to acquire the reload lock, return the current state
        # if stamps have changed, reload the state
        _reload = self._reload
        if _reload is None:
            return self._state
        _now = time.monotonic()
        if _now < self._next_check:
            return self._state
        # Another thread is already reloading, serve the state in hand
        if not self._reload_lock.acquire(blocking=False):
            return self._state
        try:
            self._next_check: float = _now + self._reload_interval
            _old: TokenAuthState = self._state
            _stamps: dict[Path, _FileStamp] = self._stamp((_old.masterfile, *self._watch))
            if _stamps != _old.stamps:
                self._state = self._reloaded(_reload, _old, _stamps)
            return self._state
        finally:
            self._reload_lock.release()

    def _reloaded(
        self,
        reload: Callable[[], AuthSetting],
        old: TokenAuthState,
        stamps: dict[Path, _FileStamp],
    ) -> TokenAuthState:
        try:
            _setting: AuthSetting = reload()
            _new: TokenAuthState = self._build(_setting)
        except Exception as e:
            # The failed stamps are kept
            # so it is retried only when a file changes again
            self._log_failure(e)
            _replace = old.clone(stamps=stamps)
            return _replace

        if self._log is not None:
            self._log.info(
                "auth reloaded",
                metadata={"tokens": len(_new.entries)},
            )
        return _new

    def _log_failure(
        self,
        error: Exception,
    ) -> None:
        if self._log is None:
            return
        # The errors of this module never carry the key
        self._log.error(
            "auth reload failed, rollback to previous state",
            metadata={
                "error": type(error).__name__,
                "detail": str(error),
            },
        )

    @staticmethod
    def _resolve_masterfile(
        setting: AuthSetting,
        base_dir: Path | None,
    ) -> Path:
        _path: Path = Path(setting.masterfile).expanduser()
        if not _path.is_absolute():
            _path = (base_dir or Path.cwd()) / _path
        return _path.resolve()

    def _today(self) -> date:
        return IClock.current(timezone="UTC").date()

    @classmethod
    def _read_masterkey(
        cls,
        masterfile: Path,
    ) -> bytes:
        if not masterfile.is_file():
            raise FileNotFoundError(f"masterfile not found: {masterfile}")
        if os.name == "posix" and masterfile.stat().st_mode & 0o077:
            raise PermissionError(f"masterfile {masterfile} is accessible by group or others, run: chmod 600")

        # Never put the content into an error message
        _key: str = masterfile.read_text(encoding="utf-8").strip()
        _min_length: int = cls._min_masterkey_length
        if len(_key) < _min_length:
            raise ValueError(f"masterkey in {masterfile} is shorter than {_min_length}")
        _encoded: bytes = _key.encode("utf-8")
        return _encoded

    @classmethod
    def generate_master_file(
        cls,
        setting: AuthSetting,
        base_dir: Path | None = None,
    ) -> Path | None:
        # Not an instance method, the constructor needs the file to exist
        _path: Path = cls._resolve_masterfile(setting, base_dir)
        if _path.exists():
            return None
        _path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _flags: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        _mode: int = 0o600
        try:
            _fd = os.open(_path, _flags, _mode)
        except FileExistsError:
            return None
        with os.fdopen(_fd, "w", encoding="utf-8") as f:
            _content: str = secrets.token_hex(cls._min_masterkey_length)
            f.write(_content + "\n")
        return _path

    def state(
        self,
        name: str,
    ) -> str:
        # Retrieve the current state of the token with the given name
        _entry = self._current().entries.get(name)
        if _entry is None:
            raise ValueError(f"unknown token {name!r}")
        _token_state: str = self._state_of(_entry)
        return _token_state

    def token(
        self,
        name: str,
    ) -> str:
        """Retrieve the token string for a given token name."""
        _current: TokenAuthState = self._current()
        _entry: TokenSetting | None = _current.entries.get(name)
        if _entry is None:
            raise ValueError(f"unknown token {name!r}")
        _token_state: str = self._state_of(_entry)
        if _token_state != "active":
            raise ValueError(f"token {name!r} is {_token_state}")
        _mac_res: str = self._mac(_current.masterkey, _entry)
        return _mac_res

    def verify(
        self,
        raw: str,
    ) -> Principal:
        """Verify a raw token and return the corresponding principal."""
        if not isinstance(raw, str) or len(raw) != 64:
            raise AuthError("malformed")

        _current: TokenAuthState = self._current()
        _raw: bytes = raw.encode()
        _hit: TokenSetting | None = None
        for _entry in _current.entries.values():
            _mac_encoded = self._mac(_current.masterkey, _entry).encode()
            if hmac.compare_digest(_mac_encoded, _raw):
                _hit: TokenSetting = _entry

        if _hit is None:
            raise AuthError("mismatch")

        _token_state: str = self._state_of(_hit)
        if _token_state != "active":
            raise AuthError(_token_state)

        _principal: Principal = Principal(
            name=_hit.name,
            description=_hit.description,
            delegate=_hit.delegate,
        )
        return _principal

    def _state_of(
        self,
        entry: TokenSetting,
    ) -> str:
        if entry.revoked:
            return "revoked"
        if entry.expires is not None and self._today() > entry.expires:
            return "expired"
        return "active"

    @classmethod
    def _mac(
        cls,
        masterkey: bytes,
        entry: TokenSetting,
    ) -> str:
        """Compute the HMAC of a token entry using the master key."""
        _msg = f"{cls._domain_name}:{entry.name}:{entry.version}".encode()
        _mac: str = hmac.new(masterkey, _msg, hashlib.sha256).hexdigest()
        return _mac
