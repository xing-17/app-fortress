from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from bastion.control.run.run import Run
from bastion.control.store.base.base import IStoreLike

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.domain.run import RunModel


class LocalStore(IStoreLike):
    def __init__(
        self,
        name: str = "default",
        path: str | Path | None = None,
    ) -> None:
        self.name: str = name
        self.path: Path = self._resolve_path(path)
        self._conn = self._resolve_conn()
        self._table_runs = "_bas_runs"
        self.init()

    def _resolve_path(
        self,
        path: str | Path | None = None,
    ) -> Path:
        if not path:
            path = Path(".bastion") / "store" / f"{self.name}.db"
            return path.expanduser().resolve()
        else:
            _path = Path(path)
            if _path.is_dir():
                _path = _path / f"{self.name}.db"
            return _path.expanduser().resolve()

    def _resolve_conn(self) -> duckdb.DuckDBPyConnection:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        return duckdb.connect(str(self.path))

    def init(self) -> None:
        _run_table_ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table_runs} ("
            f"    id VARCHAR PRIMARY KEY,"
            f"    compute_name VARCHAR NOT NULL,"
            f"    created_at VARCHAR NOT NULL,"
            f"    data JSON NOT NULL"
            f")"
        )
        self._conn.execute(_run_table_ddl)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> LocalStore:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def save_run(
        self,
        run: IRunLike | RunModel,
    ) -> None:
        # Align as domain model
        domain = run.domain if isinstance(run, Run) else run

        # Save the run data to the database
        _id: str = domain.id
        _compute_name: str = domain.compute_name
        _created_at: str = domain.created_at.isoformat()
        _data_str: str = json.dumps(domain.export())
        _insert_sql = (
            f"INSERT INTO {self._table_runs}"
            f" (id, compute_name, created_at, data)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET"
            " compute_name = excluded.compute_name,"
            " created_at = excluded.created_at,"
            " data = excluded.data"
        )
        _params = [_id, _compute_name, _created_at, _data_str]
        self._conn.execute(_insert_sql, _params)

    def get_run(
        self,
        run_id: str,
    ) -> IRunLike | None:
        # Fetch the run data from the database
        _params = [run_id]
        _sql = f"SELECT data FROM {self._table_runs} WHERE id = ?"
        row = self._conn.execute(_sql, _params).fetchone()
        if row is None:
            return None
        else:
            _data: dict = json.loads(row[0])
            return Run.from_dict(_data)

    def _build_run_query(
        self,
        compute_name: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[str, list]:
        _params: list = []
        _select_sql = f"SELECT data FROM {self._table_runs}"
        if compute_name or since or until:
            _select_sql += " WHERE "
            _clauses = []
            for _field, _value in [
                ("compute_name = ?", compute_name),
                ("created_at > ?", since.isoformat() if since else None),
                ("created_at < ?", until.isoformat() if until else None),
            ]:
                if _value is not None:
                    _clauses.append(_field)
                    _params.append(_value)
            _select_sql += " AND ".join(_clauses)

        if limit is not None:
            _select_sql += " LIMIT ?"
            _params.append(limit)
        return _select_sql, _params

    def list_runs(
        self,
        compute_name: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[Run]:
        _sql, _params = self._build_run_query(
            compute_name=compute_name,
            since=since,
            until=until,
            limit=limit,
        )
        rows = self._conn.execute(_sql, _params).fetchall()
        _result = []
        for r in rows:
            _data: dict = json.loads(r[0])
            _result.append(Run.from_dict(_data))
        return _result

    def delete_run(
        self,
        run_id: str,
    ) -> None:
        _sql = f"DELETE FROM {self._table_runs} WHERE id = ?"
        self._conn.execute(_sql, [run_id])
