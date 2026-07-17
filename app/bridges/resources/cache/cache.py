from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import duckdb
import polars as pl

from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesCacheSetting


class BridgesCache(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    Bridges 缓存层（DuckDB + Polars）

    每条缓存记录由 (key, partition) 唯一标识，数据存储为独立的 DuckDB 表，
    TTL 元数据统一记录在 __system_ttl 表中，过期条目自动清理。

    Attributes:
        conn:  DuckDB 连接实例（公开，供外部调试使用）

    Methods:
        read(key, partition, ttl_hours): 读取缓存数据，返回 Polars DataFrame 或 None
        write(key, data, partition, ttl_hours): 写入缓存数据，支持 Polars DataFrame 或 list[dict]
        check(key, partition): 检查缓存是否存在且未过期，返回布尔值
        reset(key, partition): 重置缓存，删除指定的缓存条目
        refresh(): 刷新缓存配置，重新连接 DuckDB 并清理过期条目

    Example:
        >>> cache = BridgesCache()
        >>> cache.write("stock_tradedates", df)
        >>> df = cache.read("stock_tradedates")
        >>> cache.check("stock_tradedates")   # True
        >>> cache.reset()                     # 清空全部

    """

    @classmethod
    def load(cls) -> BridgesCache:
        return cls()

    def __init__(self) -> None:
        super().__init__()
        self._lock: threading.Lock = threading.Lock()

        # Basic attributes
        self._name: str = self.setting.name
        self._path: Path = self._resolve_path()
        self._ttl_hours: int = self.setting.ttl_hours
        self._ttl_table: str = self.setting.ttl_table
        self._hash_length: int = self.setting.hash_length
        self._set_log_prefix(f"BridgesCache({self._name})")

        # Set up DuckDB connection and TTL table
        self.conn: duckdb.DuckDBPyConnection = self._resolve_connection()
        self.ensure_ttl_table()

        # Set logging attributes
        self.info("init: OK.")
        self.clean()

    @property
    def setting(self) -> BridgesCacheSetting:
        return GlobalSetting.bridges.cache

    def _resolve_path(self) -> Path:
        path = Path(self.setting.path).expanduser().resolve()
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        return path

    def _resolve_connection(self) -> duckdb.DuckDBPyConnection:
        conn = duckdb.connect(
            database=str(self._path),
            read_only=False,
        )
        timezone = GlobalSetting.system.timezone
        conn.execute("SET TimeZone = ?", [timezone])
        self.debug(f"_resolve_connection: timezone set to '{timezone}' OK.")
        return conn

    def ensure_ttl_table(self) -> str:
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._ttl_table} (
                key          VARCHAR     PRIMARY KEY,
                expire_at    TIMESTAMPTZ NOT NULL
            )
        """)
        self.debug(f"ensure_ttl_table: '{self._ttl_table}' OK.")
        return self._ttl_table

    def connect(self) -> None:
        if not hasattr(self, "conn") or not self.conn:
            self.conn = self._resolve_connection()
            self.ensure_ttl_table()

    def close(self) -> None:
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
            self.conn = None
            self.info("close: OK.")

    def __enter__(self) -> BridgesCache:
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def resolve_identifier(
        self,
        key: str,
        partition: str | list[str] | None = None,
    ) -> str:
        if partition is None:
            parts: list[str] = []
        elif isinstance(partition, str):
            parts = [partition]
        else:
            parts = list(partition)
        parts = sorted(parts)
        parts_text = "|".join(parts)
        value = f"{key}|{parts_text}"
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[: self._hash_length]

    def resolve_ttl_hours(
        self,
        ttl_hours: int | None = None,
    ) -> int:
        if ttl_hours is None:
            ttl_hours = self._ttl_hours
        return ttl_hours

    def resolve_data(
        self,
        data: pl.DataFrame | list[dict],
    ) -> pl.DataFrame:
        if isinstance(data, pl.DataFrame):
            return data
        elif isinstance(data, list):
            return pl.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    def _list_tables(self) -> list[str]:
        query = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE TRUE
                AND table_schema = 'main'
                AND table_name != '{self._ttl_table}'
        """
        rows: list[tuple[str]] = self.conn.execute(query).fetchall()
        result = [row[0] for row in rows]
        return result

    def _check_exist(
        self,
        table: str,
    ) -> bool:
        query = """
            SELECT count(*) 
            FROM information_schema.tables
            WHERE table_name = ?
        """
        row = self.conn.execute(query, [table]).fetchone()
        result = bool(row and row[0] > 0)
        return result

    def _check_valid(
        self,
        identifier: str,
    ) -> bool:
        current_ts: float = self._get_current_timestamp()
        query = f"""
            SELECT key 
            FROM {self._ttl_table}
            WHERE TRUE
                AND key = ?
                AND expire_at > to_timestamp(?)
        """
        row: list[tuple[str]] = self.conn.execute(
            query=query,
            parameters=[identifier, current_ts],
        ).fetchall()
        return True if row else False

    def _delete_table(
        self,
        identifier: str,
    ) -> None:
        self.conn.execute(
            f'DROP TABLE IF EXISTS "{identifier}"',
        )
        self.conn.execute(
            f"DELETE FROM {self._ttl_table} WHERE key = ?",
            [identifier],
        )

    def _clean_expired_entries(
        self,
        identifier: str | None = None,
    ) -> int:
        n_count = 0
        if identifier is None:
            for _identifier in self._list_tables():
                if not self._check_valid(_identifier):
                    self._delete_table(_identifier)
                    n_count += 1
        else:
            if not self._check_valid(identifier):
                self._delete_table(identifier)
                n_count += 1
        return n_count

    def check(
        self,
        key: str,
        partition: str | list[str] | None = None,
    ) -> bool:
        result = False
        identifier: str = self.resolve_identifier(key, partition)
        self.tick("check")
        with self._lock:
            if not self._check_exist(identifier):
                self.debug(f"check: '{identifier}' does not exist.")
                result = False
            elif not self._check_valid(identifier):
                self.debug(f"check: '{identifier}' has expired.")
                self._clean_expired_entries(identifier)
                result = False
            else:
                self.debug(f"check: '{identifier}' found.")
                result = True
        seconds = self.tock("check")
        self.debug(f"check: duration {seconds:.3f}s.")
        return result

    def read(
        self,
        key: str,
        partition: str | list[str] | None = None,
    ) -> pl.DataFrame | None:
        self.tick("read")
        identifier = self.resolve_identifier(key, partition)
        with self._lock:
            if not self._check_exist(identifier):
                self.debug(f"read: '{identifier}' does not exist.")
                return None
            if not self._check_valid(identifier):
                self.debug(f"read: '{identifier}' has expired.")
                self._clean_expired_entries(identifier)
                return None
            query = f'SELECT * FROM "{identifier}"'
            result = self.conn.execute(query).pl()
            self.debug(
                f"read: {len(result)} rows read from '{identifier}' OK.",
                context={
                    "identifier": identifier,
                    "key": key,
                    "partition": partition,
                    "rows": len(result),
                },
            )
            seconds = self.tock("read")
            self.debug(f"read: duration {seconds:.3f}s.")
            return result

    def write(
        self,
        key: str,
        data: pl.DataFrame,
        partition: str | list[str] | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        self.tick("write")
        current_ts: float = self._get_current_timestamp()
        ttl_hours = self.resolve_ttl_hours(ttl_hours)
        expire_ts: float = current_ts + ttl_hours * 60 * 60
        data = self.resolve_data(data)
        with self._lock:
            identifier = self.resolve_identifier(key, partition)
            buffer_table = "_write_buffer"
            self.conn.register(buffer_table, data.to_arrow())
            try:
                self.conn.execute("BEGIN")
                self.conn.execute(f"""
                    CREATE OR REPLACE TABLE "{identifier}" AS
                    SELECT * FROM {buffer_table}
                """)
                self.conn.execute(
                    f"""
                    INSERT INTO {self._ttl_table} (key, expire_at)
                    VALUES (?, to_timestamp(?))
                    ON CONFLICT (key) DO UPDATE SET expire_at = excluded.expire_at
                """,
                    [identifier, expire_ts],
                )
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
            finally:
                self.conn.unregister(buffer_table)

            seconds = self.tock("write")
            self.debug(
                f"write: '{identifier}' {len(data)} rows OK.",
                context={
                    "key": identifier,
                    "partition": partition,
                    "rows": len(data),
                    "ttl_hours": ttl_hours,
                    "expires_at": expire_ts,
                },
            )
            self.debug(f"write: duration {seconds:.3f}s.")

    def reset(
        self,
        key: str | None = None,
        partition: str | list[str] | None = None,
    ) -> None:
        # Reset cache entries.
        self.tick("reset")
        with self._lock:
            if key is None:
                # 删除全部
                identifiers = self._list_tables()
                for identifier in identifiers:
                    self._delete_table(identifier)
                self.debug(f"reset: {len(identifiers)} rows OK.")
            else:
                identifier = self.resolve_identifier(key, partition)
                if self._check_exist(identifier):
                    self._delete_table(identifier)
                    self.debug(f"reset: '{identifier}' OK.")
                else:
                    self.warning(f"reset: '{identifier}' not found.")

        seconds = self.tock("reset")
        self.debug(f"reset: duration {seconds:.3f}s.")

    def clean(
        self,
        key: str | None = None,
        partition: str | list[str] | None = None,
    ) -> None:
        self.tick("clean")
        with self._lock:
            if key is None:
                n_count = self._clean_expired_entries()
                self.debug(f"clean: {n_count} expired rows OK.")
            else:
                identifier = self.resolve_identifier(key, partition)
                n_count = self._clean_expired_entries(identifier)
                if n_count < 1:
                    self.debug(f"clean: no expire entry for '{identifier}'.")
                else:
                    self.debug(f"clean: expire entry '{identifier}' OK.")
        seconds = self.tock("clean")
        self.debug(f"clean: duration {seconds:.3f}s.")

    def refresh(self) -> None:
        with self._lock:
            self.close()
            self.connect()
            self.ensure_ttl_table()
        self.clean()
        self.info("refresh: OK.")

    def export(self) -> dict:
        return {
            "name": self._name,
            "path": str(self._path),
            "ttl_hours": self._ttl_hours,
            "ttl_table": self._ttl_table,
            "hash_length": self._hash_length,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
# 通过调用 `ModuleBridgesCache.refresh()` 可在运行时刷新配置
ModuleBridgesCache: BridgesCache = BridgesCache.load()
