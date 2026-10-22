from __future__ import annotations

import threading
import time
from collections.abc import Mapping

import duckdb

from .errors import (
    DRAError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from .guard import DRAGuard
from .limits import DRALimits
from .mount import DRAMount
from .result import (
    DRAColumnDefinition,
    DRADataResult,
    DRADefinitionResult,
)

_BATCH_ROWS = 1024


class DRASession:
    """
    Read-only query session over mounted datasets

    Each mount becomes a view `<source>.<dataset>`. Only a single SELECT is accepted, reads are
    confined to the mount scopes, and the engine configuration is locked at construction, so all
    mounts must be given up front.

    Args:
    ----------
        mounts (Mapping[str, DRAMount]):
            Dataset name "<source>.<dataset>" -> mount
        limits (DRALimits | None):
            Limits, defaults when omitted

    Methods:
    ----------
        refresh(mounts):
            Update credentials before a query, nothing to do for file mounts
        definition(name):
            Live schema of a mounted dataset
        query(sql):
            Run one SELECT under the limits
        close():
            Release the engine

    """

    def __init__(
        self,
        mounts: Mapping[str, DRAMount],
        limits: DRALimits | None = None,
    ) -> None:
        if not mounts:
            raise DRARejectedError("at least one mount is required")

        self._limits = limits or DRALimits()
        self._lock = threading.RLock()
        self._closed = False
        self._partitions: dict[str, list[str]] = {}

        # Validate everything before the engine exists
        # a rejected mount leaves nothing behind.
        _checked: dict[str, tuple[str, str, str, str, DRAMount]] = {}
        for _name, _mount in mounts.items():
            _source, _dataset = DRAGuard.split_dataset_name(_name)
            _scope, _glob = DRAGuard.check_mount(_mount)
            _checked[_name] = (_source, _dataset, _scope, _glob, _mount)
        self._scopes = {name: c[2] for name, c in _checked.items()}

        _sorted_scopes = sorted(set(self._scopes.values()))
        _checked_mounts = [c[4] for c in _checked.values()]
        self._con = self._connect(_sorted_scopes, _checked_mounts)
        try:
            for _name, (_source, _dataset, _, _glob, _mount) in _checked.items():
                self._mount(_name, _source, _dataset, _glob, _mount)
        except BaseException:
            self._con.close()
            raise

    def refresh(
        self,
        mounts: Mapping[str, DRAMount],
    ) -> None:
        """
        File mounts carry no credentials, only require that the mounted set is unchanged.

        """
        _scopes = {}
        for name, m in mounts.items():
            _scopes[name] = DRAGuard.check_mount(m)[0]

        if _scopes != self._scopes:
            raise DRARejectedError("mounts changed, open a new session")

    def definition(
        self,
        name: str,
    ) -> DRADefinitionResult:
        _source, _dataset = DRAGuard.split_dataset_name(name)
        if name not in self._scopes:
            raise DRAError(f"unknown dataset {name!r}")

        with self._lock:
            self._ensure_open()
            _cur = self._con.cursor()

        try:
            _rows = _cur.execute(f'DESCRIBE "{_source}"."{_dataset}"').fetchall()
        except duckdb.Error as e:
            # The view is lazy
            # a vanished or unreadable file surfaces here.
            raise DRAQueryError(f"cannot describe {name}: {e}") from e
        finally:
            _cur.close()

        _cols: list[DRAColumnDefinition] = []
        for row in _rows:
            _col_name: str = row[0]
            _col_type: str = row[1]
            _col_nullable: bool = row[2] == "YES"
            _col_def: DRAColumnDefinition = DRAColumnDefinition(
                name=_col_name,
                type=_col_type,
                nullable=_col_nullable,
            )
            _cols.append(_col_def)

        return DRADefinitionResult(
            dataset=name,
            columns=_cols,
            partitions=list(self._partitions[name]),
        )

    def query(
        self,
        sql: str,
    ) -> DRADataResult:
        with self._lock:
            self._ensure_open()
            DRAGuard.check_statement(self._con, sql)
            _cur = self._con.cursor()
        return self._fetch(_cur, sql)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._con.close()

    def __enter__(self) -> DRASession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise DRAError("session is closed")

    def _connect(
        self,
        scopes: list[str],
        mounts: list[DRAMount] | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """In-memory engine confined to `scopes`, configuration locked."""
        _con = duckdb.connect(":memory:")
        _s3 = [m for m in mounts or [] if m.scheme == "s3"]
        if _s3:
            # The extension and the secrets must be in place before external access is turned off.
            _con.execute("LOAD httpfs")
            for _i, _m in enumerate(_s3):
                _con.execute(self._secret_sql(f"dra_s3_{_i}", _m))
        # No spilling: with external access off the engine
        # aborts the process when it cleans up its temp dir.
        _con.execute("SET temp_directory=''")
        _dirs = ", ".join(DRAGuard.stringify_sql(s) for s in scopes)
        # Order matters: allowed_directories can not be set
        # once external access is off or the config is locked.
        _con.execute(f"SET allowed_directories=[{_dirs}]")
        _con.execute("SET enable_external_access=false")
        _con.execute("SET autoinstall_known_extensions=false")
        _con.execute("SET autoload_known_extensions=false")
        _con.execute(f"SET memory_limit='{self._limits.memory_limit_mb}MB'")
        _con.execute(f"SET threads={self._limits.threads}")
        _con.execute("SET lock_configuration=true")
        return _con

    @staticmethod
    def _secret_sql(name: str, m: DRAMount) -> str:
        _q = DRAGuard.stringify_sql
        _parts = [
            "TYPE s3",
            f"ENDPOINT {_q(m.endpoint)}",
            f"REGION {_q(m.region)}",
            f"URL_STYLE {_q(m.url_style)}",
            f"USE_SSL {'true' if m.use_ssl else 'false'}",
            f"SCOPE {_q(m.scope)}",
        ]
        if m.key_id is not None:
            _key_id: str = m.key_id
            _secret: str = m.secret.get_secret_value()
            _parts += [
                f"KEY_ID {_q(_key_id)}",
                f"SECRET {_q(_secret)}",
            ]
        if m.session_token is not None:
            _session_token: str = m.session_token.get_secret_value()
            _parts.append(f"SESSION_TOKEN {_q(_session_token)}")
        return f"CREATE SECRET {name} ({', '.join(_parts)})"

    def _mount(
        self,
        name: str,
        source: str,
        dataset: str,
        glob: str,
        mount: DRAMount,
    ) -> None:
        # Declared partitions come from the directory names,
        # as VARCHAR, the SQL casts what it needs.
        if mount.partitions:
            _options = "hive_partitioning=true, hive_types_autocast=false"
        else:
            _options = "hive_partitioning=false"
        self._con.execute(f'CREATE SCHEMA IF NOT EXISTS "{source}"')
        try:
            _glob: str = DRAGuard.stringify_sql(glob)
            self._con.execute(
                f'CREATE OR REPLACE VIEW "{source}"."{dataset}" AS '
                f"SELECT * FROM read_parquet({_glob}, {_options}, union_by_name=true)"
            )
        except duckdb.Error as e:
            raise DRAQueryError(f"cannot mount {name}: {e}") from e
        self._partitions[name] = list(mount.partitions)

    def _fetch(
        self,
        cur: duckdb.DuckDBPyConnection,
        sql: str,
    ) -> DRADataResult:
        """Run one validated statement on `cur` with the timeout and the row/size caps applied."""
        _limits = self._limits
        _max_bytes = int(_limits.max_result_mb * 1024 * 1024)
        _timed_out = threading.Event()

        def _stop() -> None:
            _timed_out.set()
            cur.interrupt()

        # Interrupt must hit the cursor that runs the query, not the parent connection.
        _timer = threading.Timer(_limits.timeout_seconds, _stop)
        _timer.daemon = True
        _start = time.perf_counter()
        _timer.start()
        try:
            cur.execute(sql)
            _columns = [d[0] for d in cur.description]
            _types = [str(d[1]) for d in cur.description]
            _rows: list[list] = []
            _size = 0
            _truncated_by = None
            for _batch in cur.to_arrow_reader(_BATCH_ROWS):
                _room = _limits.max_rows - len(_rows)
                if _batch.num_rows > _room:
                    _batch = _batch.slice(0, _room)
                    _truncated_by = "rows"
                if _size + _batch.nbytes > _max_bytes:
                    # Keep the share of rows that fits
                    # so a tiny cap still returns something.
                    _fit = int((_max_bytes - _size) * _batch.num_rows / _batch.nbytes)
                    _batch = _batch.slice(0, _fit)
                    _truncated_by = "size"
                _size += _batch.nbytes
                _rows.extend(list(r) for r in zip(*(c.to_pylist() for c in _batch.columns)))
                if _truncated_by:
                    break
        except duckdb.Error as e:
            if _timed_out.is_set():
                raise DRAQueryTimeoutError(f"query exceeded {_limits.timeout_seconds}s") from e
            if isinstance(e, duckdb.InterruptException):
                raise DRAQueryError(str(e)) from e
            raise DRAQueryError(f"{type(e).__name__}: {e}") from e
        finally:
            _timer.cancel()
            cur.close()

        return DRADataResult(
            columns=_columns,
            types=_types,
            rows=_rows,
            truncated=_truncated_by is not None,
            truncated_by=_truncated_by,
            elapsed_ms=round((time.perf_counter() - _start) * 1000, 3),
        )
