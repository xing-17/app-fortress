from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, Literal

import duckdb
from pydantic import Field, PrivateAttr, model_validator

from app.internal.constant.platform import Platform
from app.internal.util.path import IPath
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._base import BaseStore
from app.setting._store import LocalStoreSetting

_DEFAULT_PATH = Path("./.store/local/")
_REGEX_NAME = r"^[a-zA-Z0-9_\-]+$"


class DuckDbStore(BaseStore):
    """
    Local DuckDB store resource.

    Args:
        name (str):
            Name of the DuckDB store.
        path (str | None):
            Path to the DuckDB database file.
        config (dict[str, Any]):
            Configuration for the DuckDB connection.
        identity (LocalIdentity):
            Local identity associated with the DuckDB store.
        tags (dict[str, Any] | None):
            Tags associated with the store.

    Attributes:
        conn (duckdb.DuckDBPyConnection):
            Cached DuckDB connection instance.

    Methods:
        from_setting(setting: LocalStoreSetting) -> "DuckDbStore":
            Creates a DuckDbStore instance from the given LocalStoreSetting.
        close() -> None:
            Closes the DuckDB connection if it is open.
        describe() -> str:
            Returns a JSON-formatted string describing the store.
        export() -> dict[str, Any]:
            Returns a dictionary containing the store's details.

    Examples:
        >>> store = DuckDbStore(
        ...     name="my-duckdb-store",
        ...     path="./.store/local/",
        ...     config={},
        ...     identity=LocalIdentity.default(),
        ... )
        >>> store.describe()
        >>> store.conn  # Access the cached DuckDB connection instance

    """

    # Inherited from BaseStore
    # - name: str
    # - tags: dict[str, Any]
    platform: Literal[Platform.LOCAL] = Platform.LOCAL
    path: str | None = Field(
        default=None,
        description="Path to the DuckDB database file",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Configuration for the DuckDB connection",
    )
    identity: LocalIdentity = Field(
        default_factory=LocalIdentity.default,
        description="[NoOps] Local identity associated with the DuckDB store",
    )

    _path: Path | None = PrivateAttr(default=None)
    _file: Path | None = PrivateAttr(default=None)
    _conn: duckdb.DuckDBPyConnection | None = PrivateAttr(default=None)
    _conn_lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_path(self) -> "DuckDbStore":
        if not re.match(_REGEX_NAME, self.name):
            raise ValueError(f"Name '{self.name}' not match REG '{_REGEX_NAME}'")
        _resolved = IPath.resolve(
            value=self.path,
            default=_DEFAULT_PATH,
            ensure=True,
        )
        self._path = _resolved
        self._file = self._path / f"{self.name}.db"
        return self

    @classmethod
    def from_setting(
        cls,
        setting: LocalStoreSetting,
    ) -> "DuckDbStore":
        return cls(
            name=setting.name,
            platform=setting.platform,
            path=setting.path,
            config=setting.config,
            identity=GlobalIdentities.get_identity(
                name=getattr(setting, "identity", None),
                strict=False,
            )
            or LocalIdentity.default(),
            tags=setting.tags,
        )

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            with self._conn_lock:
                if self._conn is None:
                    self._conn = duckdb.connect(
                        database=str(self._file),
                        read_only=False,
                        config=self.config,
                    )
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            with self._conn_lock:
                if self._conn is not None:
                    self._conn.close()
                    self._conn = None

    def __enter__(self) -> "DuckDbStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = super().export()
        _res["identity"] = self.identity.name
        return _res
