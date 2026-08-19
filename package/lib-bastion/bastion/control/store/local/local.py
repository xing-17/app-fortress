from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import duckdb

from bastion._internal.object import IBastionObject
from bastion.control.bridge.bridge import Bridge, BridgeModel
from bastion.control.run.run import Run, RunModel
from bastion.control.store.base.base import IStoreLike
from bastion.domain.store.base import BaseStoreModel, StoreKind

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

logger = logging.getLogger(__name__)


class LocalStoreModel(BaseStoreModel):
    kind: StoreKind = StoreKind.LOCAL
    path: str = "./data/store.duckdb"
    table_bridges: str = "_bridges"
    table_runs: str = "_runs"


class LocalStore(
    IBastionObject,
    IStoreLike,
):
    _domain_class = LocalStoreModel

    def __init__(
        self,
        name: str,
        path: str | Path,
        table_bridges: str = "_bridges",
        table_runs: str = "_runs",
    ) -> None:
        if not _SAFE_IDENT.match(table_bridges) or not _SAFE_IDENT.match(table_runs):
            raise ValueError("Table names must be valid SQL identifiers")

        super().__init__(
            name=name,
            path=str(path),
            table_bridges=table_bridges,
            table_runs=table_runs,
        )
        self._path = self._resolve_path(path)
        self._ensure_path()
        self._conn = self._resolve_conn()
        self._init()

    @property
    def _ensure_table_bridges_sql(self) -> str:
        _sql = f"CREATE TABLE IF NOT EXISTS {self.table_bridges} ("
        _sql += "name VARCHAR PRIMARY KEY, "
        _sql += "data JSON NOT NULL"
        _sql += ")"
        return _sql

    @property
    def _ensure_table_runs_sql(self) -> str:
        _sql = f"CREATE TABLE IF NOT EXISTS {self.table_runs} ("
        _sql += "id VARCHAR PRIMARY KEY, "
        _sql += "bridge_name VARCHAR NOT NULL, "
        _sql += "created_at TIMESTAMPTZ NOT NULL, "
        _sql += "data JSON NOT NULL"
        _sql += ")"
        return _sql

    @property
    def _ensure_index_sql(self) -> str:
        _sql = f"CREATE INDEX IF NOT EXISTS idx_runs_bridge ON {self.table_runs} "
        _sql += " (bridge_name, created_at)"
        return _sql

    def _init(self) -> None:
        self._conn.execute(self._ensure_table_bridges_sql)
        self._conn.execute(self._ensure_table_runs_sql)
        self._conn.execute(self._ensure_index_sql)

    def _resolve_path(
        self,
        path: str | Path,
    ) -> Path:
        return Path(path).expanduser().resolve()

    def _ensure_path(
        self,
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _resolve_conn(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self._path))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> LocalStore:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Bridge
    # ------------------------------------------------------------------
    def check_bridge_exists(
        self,
        name: str,
    ) -> bool:
        _sql = f"SELECT 1 FROM {self.table_bridges} WHERE name = ?"
        row = self._conn.execute(_sql, [name]).fetchone()
        return row is not None

    def save_bridge(
        self,
        bridge: Bridge | BridgeModel,
    ) -> None:
        if isinstance(bridge, Bridge):
            bridge: BridgeModel = bridge.domain

        # Save the bridge to the database
        _name: str = bridge.name
        _data: dict = bridge.export()
        _data_str: str = json.dumps(_data)
        _sql = f"INSERT INTO {self.table_bridges} (name, data) VALUES (?, ?)"
        _sql += " ON CONFLICT (name) DO UPDATE SET data = excluded.data"
        self._conn.execute(_sql, [_name, _data_str])

    def get_bridge(
        self,
        name: str,
    ) -> Bridge | None:
        _sql = f"SELECT data FROM {self.table_bridges} WHERE name = ?"
        row = self._conn.execute(_sql, [name]).fetchone()
        if row is None:
            return None
        else:
            _data: dict = json.loads(row[0])
            return Bridge.from_dict(_data)

    def delete_bridge(
        self,
        name: str,
    ) -> None:
        _sql = f"DELETE FROM {self.table_bridges} WHERE name = ?"
        self._conn.execute(_sql, [name])

    def list_bridges(
        self,
        limit: int | None = None,
    ) -> list[Bridge]:
        _sql = f"SELECT data FROM {self.table_bridges}"
        if limit is not None:
            _sql += " LIMIT ?"
            rows = self._conn.execute(_sql, [limit]).fetchall()
        else:
            rows = self._conn.execute(_sql).fetchall()
        _result = []
        for r in rows:
            _data: dict = json.loads(r[0])
            _result.append(Bridge.from_dict(_data))
        return _result

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def check_run_exists(
        self,
        run_id: str,
    ) -> bool:
        _sql = f"SELECT 1 FROM {self.table_runs} WHERE id = ?"
        row = self._conn.execute(_sql, [run_id]).fetchone()
        return row is not None

    def save_run(
        self,
        run: Run | RunModel,
    ) -> None:
        if isinstance(run, Run):
            run: RunModel = run.domain

        _id: str = run.id
        _bridge_name: str = run.bridge_name
        _created_at: str = run.created_at.isoformat()
        _data: dict = run.export()
        _data_str: str = json.dumps(_data)
        _sql = (
            f"INSERT INTO {self.table_runs} (id, bridge_name, created_at, data) VALUES (?, ?, ?, ?)"
        )
        _sql += " ON CONFLICT (id) DO UPDATE SET"
        _sql += " bridge_name = excluded.bridge_name,"
        _sql += " created_at = excluded.created_at,"
        _sql += " data = excluded.data"
        self._conn.execute(_sql, [_id, _bridge_name, _created_at, _data_str])

    def get_run(
        self,
        run_id: str,
    ) -> Run | None:
        # Fetch the run data from the database
        _sql = f"SELECT data FROM {self.table_runs} WHERE id = ?"
        row = self._conn.execute(_sql, [run_id]).fetchone()
        if row is None:
            return None
        else:
            _data: dict = json.loads(row[0])
            return Run.from_dict(_data)

    def delete_run(
        self,
        run_id: str,
    ) -> None:
        _sql = f"DELETE FROM {self.table_runs} WHERE id = ?"
        self._conn.execute(_sql, [run_id])

    def delete_runs(
        self,
        bridge_name: str,
    ) -> None:
        _sql = f"DELETE FROM {self.table_runs} WHERE bridge_name = ?"
        self._conn.execute(_sql, [bridge_name])

    def list_runs(
        self,
        bridge_name: str | None = None,
        limit: int | None = None,
    ) -> list[Run]:
        if bridge_name is not None:
            _sql = (
                f"SELECT data FROM {self.table_runs} WHERE bridge_name = ? ORDER BY created_at DESC"
            )
            params: list = [bridge_name]
        else:
            _sql = f"SELECT data FROM {self.table_runs} ORDER BY created_at DESC"
            params = []

        if limit is not None:
            _sql += " LIMIT ?"
            params.append(limit)

        rows = self._conn.execute(_sql, params).fetchall()
        _result = []
        for r in rows:
            _data: dict = json.loads(r[0])
            _result.append(Run.from_dict(_data))
        return _result

    def _get_counts(self) -> dict[str, int]:
        _sql_bridges = f"SELECT COUNT(*) FROM {self.table_bridges}"
        _sql_runs = f"SELECT COUNT(*) FROM {self.table_runs}"
        _count_bridges: int = self._conn.execute(_sql_bridges).fetchone()[0]
        _count_runs: int = self._conn.execute(_sql_runs).fetchone()[0]
        return {
            "bridges": _count_bridges,
            "runs": _count_runs,
        }

    def export(self) -> dict[str, any]:
        _super_export: dict[str, any] = super().export()
        _counts: dict[str, int] = self._get_counts()
        _super_export["counts"] = _counts
        return _super_export
