from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import date
from pathlib import Path

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.util.clock import IClock
from app.setting.service import AuthSetting, TokenSetting


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

    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        ...,
        description="[Required] Token name",
    )
    description: str = Field(
        default="",
        description="[Optional] What the token is for",
    )


class NodeAuth:
    """
    Bearer token auth, tokens are derived from a master key and never stored

    token = <hex(HMAC-SHA256(master_key, "fortress-token-v1:<name>:<version>"))>

    Bump `version` of an entry to rotate its token, set `revoked` or remove the entry to kill it.
    Changes to the entries need a restart of the node to take effect.


    Args:
    ----------
        setting (AuthSetting):
            Auth setting with the master key file and the token entries
        base_dir (Path | None):
            Base of a relative masterfile, the settings directory, defaults to the working directory

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
    ) -> None:
        self._setting = setting
        self._masterfile: Path = self._resolve_masterfile(setting, base_dir)
        self._masterkey = self._read_masterkey()
        self._entries: dict[str, TokenSetting] = {}
        for _token in setting.tokens:
            self._entries[_token.name] = _token

    @property
    def setting(self) -> AuthSetting:
        return self._setting

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

    def _read_masterkey(self) -> bytes:
        if not self._masterfile.is_file():
            raise FileNotFoundError(f"masterfile not found: {self._masterfile}")
        if os.name == "posix" and self._masterfile.stat().st_mode & 0o077:
            raise PermissionError(f"masterfile {self._masterfile} is accessible by group or others, run: chmod 600")

        # Never put the content into an error message
        _key: str = self._masterfile.read_text(encoding="utf-8").strip()
        _min_length: int = self._min_masterkey_length
        if len(_key) < _min_length:
            raise ValueError(f"masterkey in {self._masterfile} is shorter than {_min_length}")
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
        _entry = self._entries.get(name)
        if _entry is None:
            raise ValueError(f"unknown token {name!r}")
        return self._state(_entry)

    def token(
        self,
        name: str,
    ) -> str:
        _entry = self._entries.get(name)
        if _entry is None:
            raise ValueError(f"unknown token {name!r}")
        _state = self._state(_entry)
        if _state != "active":
            raise ValueError(f"token {name!r} is {_state}")
        _mac_res: str = self._mac(_entry)
        return _mac_res

    def verify(
        self,
        raw: str,
    ) -> Principal:
        if not isinstance(raw, str) or len(raw) != 64:
            raise AuthError("malformed")

        _raw = raw.encode()
        _hit = None
        for _entry in self._entries.values():
            _mac_encoded = self._mac(_entry).encode()
            if hmac.compare_digest(_mac_encoded, _raw):
                _hit = _entry

        if _hit is None:
            raise AuthError("mismatch")

        _state = self._state(_hit)
        if _state != "active":
            raise AuthError(_state)

        _principal: Principal = Principal(
            name=_hit.name,
            description=_hit.description,
        )
        return _principal

    def _state(
        self,
        entry: TokenSetting,
    ) -> str:
        if entry.revoked:
            return "revoked"
        if entry.expires is not None and self._today() > entry.expires:
            return "expired"
        return "active"

    def _mac(
        self,
        entry: TokenSetting,
    ) -> str:
        _msg = f"{self._domain_name}:{entry.name}:{entry.version}".encode()
        _mac: str = hmac.new(self._masterkey, _msg, hashlib.sha256).hexdigest()
        return _mac
