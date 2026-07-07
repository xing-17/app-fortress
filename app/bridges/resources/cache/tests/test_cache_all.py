"""
综合测试: app.bridges.cache.cache

覆盖范围
--------
- TestResolveIdentifier     同 key+partition 哈希稳定; 顺序无关; None == 空列表; 长度由 hash_length 控制
- TestResolveTtlHours       None 回退默认值; 显式值优先
- TestResolveData           DataFrame 直通; list[dict] 转为 DataFrame; 无效类型抛 ValueError
- TestEnsureTtlTable        TTL 表初始化成功; 重复调用幂等
- TestWrite                 数据写入 DuckDB; TTL 记录使用 hash identifier; 重复写覆盖数据并更新 TTL
- TestCheck                 新写入返回 True; 不存在返回 False; 过期返回 False; 未过期返回 True
- TestRead                  有效缓存返回完整 DataFrame; 数据行完整性; 缺失返回 None; 过期返回 None
- TestReset                 单 key 删除数据表和 TTL; key=None 全量清除; 删除不存在 key 不抛异常
- TestClean                 过期条目被删除; 有效条目被保留; key=None 批量清理
- TestListTables            返回所有非 TTL 数据表; 空库返回空列表
- TestPartitionIsolation    同 key 不同 partition 产生独立表和独立 TTL
- TestContextManager        __enter__ 返回实例; __exit__ 关闭连接
- TestConcurrency           多线程并发写入不破坏数据，所有 key 均可正确读取
- TestRefresh               refresh() 重连成功; 保留有效数据; 清除过期条目
- TestExport                export() 包含必要字段; describe() 返回合法 JSON
- TestSingleton             ModuleBridgesCache 全局单例完整性
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import polars as pl
import pytest

from app.bridges.resources.cache.cache import BridgesCache, ModuleBridgesCache
from app.common.core.setting import GlobalSetting
from app.common.setting.bridges import BridgesCacheSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_SAMPLE_DF = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
_SAMPLE_LIST = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]


def _force_expire(cache: BridgesCache, identifier: str) -> None:
    cache.conn.execute(
        f"UPDATE {cache._ttl_table} SET expire_at = to_timestamp(0) WHERE key = ?",
        [identifier],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """每个测试使用独立的临时 DuckDB 文件，测试结束后关闭连接。"""
    db_path = tmp_path / "test_cache.duckdb"
    test_setting = BridgesCacheSetting(
        name="test",
        path=str(db_path),
        ttl_hours=24,
        ttl_table="__system_ttl",
        hash_length=16,
    )
    monkeypatch.setattr(BridgesCache, "setting", property(lambda self: test_setting))
    monkeypatch.setattr(GlobalSetting.system, "timezone", "UTC")

    c = BridgesCache()
    yield c
    c.close()


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveIdentifier
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveIdentifier:
    def test_same_key_partition_returns_same_hash(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("stock", ["date=2024-01-01"])
        h2 = cache.resolve_identifier("stock", ["date=2024-01-01"])
        assert h1 == h2

    def test_different_keys_return_different_hashes(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("stock_a")
        h2 = cache.resolve_identifier("stock_b")
        assert h1 != h2

    def test_partition_order_is_irrelevant(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("key", ["p=1", "p=2"])
        h2 = cache.resolve_identifier("key", ["p=2", "p=1"])
        assert h1 == h2

    def test_none_partition_equals_empty_list(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("key", None)
        h2 = cache.resolve_identifier("key", [])
        assert h1 == h2

    def test_string_partition_equals_single_element_list(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("key", "p=1")
        h2 = cache.resolve_identifier("key", ["p=1"])
        assert h1 == h2

    def test_hash_length_matches_setting(self, cache: BridgesCache):
        h = cache.resolve_identifier("key")
        assert len(h) == cache._hash_length

    def test_different_partitions_return_different_hashes(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("key", "date=2024-01-01")
        h2 = cache.resolve_identifier("key", "date=2024-01-02")
        assert h1 != h2


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveTtlHours
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveTtlHours:
    def test_none_returns_default(self, cache: BridgesCache):
        assert cache.resolve_ttl_hours(None) == cache._ttl_hours

    def test_explicit_value_overrides_default(self, cache: BridgesCache):
        assert cache.resolve_ttl_hours(10) == 10

    def test_zero_is_valid(self, cache: BridgesCache):
        assert cache.resolve_ttl_hours(0) == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveData
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveData:
    def test_dataframe_passthrough(self, cache: BridgesCache):
        result = cache.resolve_data(_SAMPLE_DF)
        assert result is _SAMPLE_DF

    def test_list_of_dicts_returns_dataframe(self, cache: BridgesCache):
        result = cache.resolve_data(_SAMPLE_LIST)
        assert isinstance(result, pl.DataFrame)
        assert len(result) == len(_SAMPLE_LIST)

    def test_list_column_names_match(self, cache: BridgesCache):
        result = cache.resolve_data(_SAMPLE_LIST)
        assert set(result.columns) == {"id", "val"}

    def test_invalid_type_raises_value_error(self, cache: BridgesCache):
        with pytest.raises(ValueError):
            cache.resolve_data("not a dataframe")  # type: ignore

    def test_invalid_dict_raises_value_error(self, cache: BridgesCache):
        with pytest.raises(ValueError):
            cache.resolve_data({"id": [1, 2]})  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# TestEnsureTtlTable
# ──────────────────────────────────────────────────────────────────────────────


class TestEnsureTtlTable:
    def test_ttl_table_exists_after_init(self, cache: BridgesCache):
        assert cache._check_exist(cache._ttl_table)

    def test_ensure_ttl_table_is_idempotent(self, cache: BridgesCache):
        # 重复调用不应抛异常
        cache.ensure_ttl_table()
        cache.ensure_ttl_table()
        assert cache._check_exist(cache._ttl_table)

    def test_ttl_table_has_correct_columns(self, cache: BridgesCache):
        row = cache.conn.execute(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{cache._ttl_table}' "
            "ORDER BY column_name"
        ).fetchall()
        columns = {r[0] for r in row}
        assert {"key", "expire_at"}.issubset(columns)


# ──────────────────────────────────────────────────────────────────────────────
# TestWrite
# ──────────────────────────────────────────────────────────────────────────────


class TestWrite:
    def test_write_creates_data_table(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        assert cache._check_exist(identifier)

    def test_write_creates_ttl_record_with_identifier(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        row = cache.conn.execute(f"SELECT key FROM {cache._ttl_table} WHERE key = ?", [identifier]).fetchone()
        assert row is not None

    def test_write_does_not_use_raw_key_in_ttl(self, cache: BridgesCache):
        cache.write("raw_key_name", _SAMPLE_DF)
        row = cache.conn.execute(f"SELECT key FROM {cache._ttl_table} WHERE key = ?", ["raw_key_name"]).fetchone()
        assert row is None  # TTL 存储的是 hash，不是原始 key

    def test_write_persists_correct_row_count(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        count = cache.conn.execute(f'SELECT count(*) FROM "{identifier}"').fetchone()[0]
        assert count == len(_SAMPLE_DF)

    def test_write_accepts_list_of_dicts(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_LIST)  # type: ignore
        assert cache.check("k1")

    def test_write_overwrites_existing_data(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        new_df = pl.DataFrame({"id": [99], "val": ["z"]})
        cache.write("k1", new_df)
        identifier = cache.resolve_identifier("k1")
        count = cache.conn.execute(f'SELECT count(*) FROM "{identifier}"').fetchone()[0]
        assert count == 1

    def test_write_updates_ttl_on_overwrite(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, ttl_hours=1)
        identifier = cache.resolve_identifier("k1")
        expire_before = cache.conn.execute(
            f"SELECT expire_at FROM {cache._ttl_table} WHERE key = ?", [identifier]
        ).fetchone()[0]

        cache.write("k1", _SAMPLE_DF, ttl_hours=48)
        expire_after = cache.conn.execute(
            f"SELECT expire_at FROM {cache._ttl_table} WHERE key = ?", [identifier]
        ).fetchone()[0]

        assert expire_after > expire_before

    def test_write_with_partition(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, partition=["date=2024-01-01"])
        assert cache.check("k1", partition=["date=2024-01-01"])


# ──────────────────────────────────────────────────────────────────────────────
# TestCheck
# ──────────────────────────────────────────────────────────────────────────────


class TestCheck:
    def test_returns_true_for_fresh_write(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        assert cache.check("k1") is True

    def test_returns_false_for_nonexistent_key(self, cache: BridgesCache):
        assert cache.check("no_such_key") is False

    def test_returns_false_for_expired_entry(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        _force_expire(cache, identifier)
        assert cache.check("k1") is False

    def test_returns_false_when_data_table_missing(self, cache: BridgesCache):
        # TTL 有记录但数据表不存在
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        cache.conn.execute(f'DROP TABLE IF EXISTS "{identifier}"')
        assert cache.check("k1") is False

    def test_partition_check_is_independent(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, partition=["p=A"])
        assert cache.check("k1", partition=["p=A"]) is True
        assert cache.check("k1", partition=["p=B"]) is False


# ──────────────────────────────────────────────────────────────────────────────
# TestRead
# ──────────────────────────────────────────────────────────────────────────────


class TestRead:
    def test_returns_dataframe_for_valid_cache(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        result = cache.read("k1")
        assert isinstance(result, pl.DataFrame)

    def test_row_count_matches_written_data(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        result = cache.read("k1")
        assert len(result) == len(_SAMPLE_DF)

    def test_column_names_match(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        result = cache.read("k1")
        assert set(result.columns) == set(_SAMPLE_DF.columns)

    def test_returns_none_for_missing_key(self, cache: BridgesCache):
        assert cache.read("no_such_key") is None

    def test_returns_none_for_expired_entry(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        _force_expire(cache, identifier)
        assert cache.read("k1") is None

    def test_data_values_are_preserved(self, cache: BridgesCache):
        df = pl.DataFrame({"x": [10, 20, 30], "y": ["p", "q", "r"]})
        cache.write("k1", df)
        result = cache.read("k1")
        assert result["x"].to_list() == [10, 20, 30]
        assert result["y"].to_list() == ["p", "q", "r"]

    def test_read_with_partition(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, partition=["date=2024-01-01"])
        result = cache.read("k1", partition=["date=2024-01-01"])
        assert result is not None
        assert len(result) == len(_SAMPLE_DF)

    def test_read_wrong_partition_returns_none(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, partition=["date=2024-01-01"])
        assert cache.read("k1", partition=["date=2024-01-02"]) is None


# ──────────────────────────────────────────────────────────────────────────────
# TestReset
# ──────────────────────────────────────────────────────────────────────────────


class TestReset:
    def test_reset_single_key_removes_data_table(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        cache.reset("k1")
        assert not cache._check_exist(identifier)

    def test_reset_single_key_removes_ttl_record(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        cache.reset("k1")
        row = cache.conn.execute(f"SELECT key FROM {cache._ttl_table} WHERE key = ?", [identifier]).fetchone()
        assert row is None

    def test_reset_nonexistent_key_does_not_raise(self, cache: BridgesCache):
        cache.reset("no_such_key")  # 不应抛异常

    def test_reset_all_removes_all_tables(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        cache.reset()
        assert cache.list_tables() == []

    def test_reset_all_clears_ttl_table(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        cache.reset()
        count = cache.conn.execute(f"SELECT count(*) FROM {cache._ttl_table}").fetchone()[0]
        assert count == 0

    def test_reset_only_affects_target_key(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        cache.reset("k1")
        assert cache.check("k1") is False
        assert cache.check("k2") is True

    def test_reset_with_partition_only_affects_that_partition(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF, partition=["p=A"])
        cache.write("k1", _SAMPLE_DF, partition=["p=B"])
        cache.reset("k1", partition=["p=A"])
        assert cache.check("k1", partition=["p=A"]) is False
        assert cache.check("k1", partition=["p=B"]) is True


# ──────────────────────────────────────────────────────────────────────────────
# TestClean
# ──────────────────────────────────────────────────────────────────────────────


class TestClean:
    def test_clean_removes_expired_entries(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        _force_expire(cache, identifier)
        cache.clean()
        assert not cache._check_exist(identifier)

    def test_clean_preserves_valid_entries(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        identifier_k1 = cache.resolve_identifier("k1")
        _force_expire(cache, identifier_k1)
        cache.clean()
        assert cache.check("k2") is True

    def test_clean_all_when_none_expired_is_no_op(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        cache.clean()
        assert cache.check("k1") is True
        assert cache.check("k2") is True

    def test_clean_single_key_removes_expired(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        _force_expire(cache, identifier)
        cache.clean("k1")
        assert cache.check("k1") is False

    def test_clean_single_valid_key_is_no_op(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.clean("k1")
        assert cache.check("k1") is True


# ──────────────────────────────────────────────────────────────────────────────
# TestListTables
# ──────────────────────────────────────────────────────────────────────────────


class TestListTables:
    def test_empty_db_returns_empty_list(self, cache: BridgesCache):
        assert cache.list_tables() == []

    def test_returns_all_data_tables(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k2", _SAMPLE_DF)
        tables = cache.list_tables()
        assert len(tables) == 2

    def test_does_not_include_ttl_table(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        tables = cache.list_tables()
        assert cache._ttl_table not in tables

    def test_count_increases_with_each_write(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        assert len(cache.list_tables()) == 1
        cache.write("k2", _SAMPLE_DF)
        assert len(cache.list_tables()) == 2

    def test_overwrite_does_not_increase_count(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.write("k1", _SAMPLE_DF)
        assert len(cache.list_tables()) == 1


# ──────────────────────────────────────────────────────────────────────────────
# TestPartitionIsolation
# ──────────────────────────────────────────────────────────────────────────────


class TestPartitionIsolation:
    def test_different_partitions_produce_different_identifiers(self, cache: BridgesCache):
        h1 = cache.resolve_identifier("key", "date=2024-01-01")
        h2 = cache.resolve_identifier("key", "date=2024-01-02")
        assert h1 != h2

    def test_partitions_are_stored_in_separate_tables(self, cache: BridgesCache):
        df_a = pl.DataFrame({"val": [1]})
        df_b = pl.DataFrame({"val": [2]})
        cache.write("key", df_a, partition=["p=A"])
        cache.write("key", df_b, partition=["p=B"])
        assert len(cache.list_tables()) == 2

    def test_partition_data_is_independent(self, cache: BridgesCache):
        df_a = pl.DataFrame({"val": [111]})
        df_b = pl.DataFrame({"val": [222]})
        cache.write("key", df_a, partition=["p=A"])
        cache.write("key", df_b, partition=["p=B"])
        assert cache.read("key", partition=["p=A"])["val"][0] == 111
        assert cache.read("key", partition=["p=B"])["val"][0] == 222

    def test_partition_ttl_is_independent(self, cache: BridgesCache):
        cache.write("key", _SAMPLE_DF, partition=["p=A"])
        cache.write("key", _SAMPLE_DF, partition=["p=B"])
        id_a = cache.resolve_identifier("key", "p=A")
        _force_expire(cache, id_a)
        assert cache.check("key", partition=["p=A"]) is False
        assert cache.check("key", partition=["p=B"]) is True

    def test_no_partition_and_with_partition_are_independent(self, cache: BridgesCache):
        cache.write("key", _SAMPLE_DF)
        cache.write("key", _SAMPLE_DF, partition=["p=X"])
        assert len(cache.list_tables()) == 2


# ──────────────────────────────────────────────────────────────────────────────
# TestContextManager
# ──────────────────────────────────────────────────────────────────────────────


class TestContextManager:
    def test_enter_returns_cache_instance(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        db_path = tmp_path / "ctx_cache.duckdb"
        test_setting = BridgesCacheSetting(name="ctx", path=str(db_path))
        monkeypatch.setattr(BridgesCache, "setting", property(lambda self: test_setting))
        monkeypatch.setattr(GlobalSetting.system, "timezone", "UTC")

        c = BridgesCache()
        with c as ctx:
            assert ctx is c

    def test_exit_closes_connection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        db_path = tmp_path / "ctx_cache2.duckdb"
        test_setting = BridgesCacheSetting(name="ctx2", path=str(db_path))
        monkeypatch.setattr(BridgesCache, "setting", property(lambda self: test_setting))
        monkeypatch.setattr(GlobalSetting.system, "timezone", "UTC")

        c = BridgesCache()
        with c:
            pass
        # 连接关闭后 DuckDB 操作应抛异常
        with pytest.raises(Exception):
            c.conn.execute("SELECT 1")


# ──────────────────────────────────────────────────────────────────────────────
# TestConcurrency
# ──────────────────────────────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_writes_all_succeed(self, cache: BridgesCache):
        """N 个线程同时写不同的 key，全部写完后所有 key 均可读取。"""
        n = 10
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                df = pl.DataFrame({"thread": [i], "val": [i * 10]})
                cache.write(f"concurrent_key_{i}", df)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"写入时发生异常: {errors}"
        for i in range(n):
            assert cache.check(f"concurrent_key_{i}") is True

    def test_concurrent_reads_do_not_corrupt_data(self, cache: BridgesCache):
        """写入后多线程并发读取，每次读取的数据应完整。"""
        df = pl.DataFrame({"x": list(range(100))})
        cache.write("shared_key", df)
        errors: list[Exception] = []
        results: list[int] = []

        def reader() -> None:
            try:
                result = cache.read("shared_key")
                if result is not None:
                    results.append(len(result))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"读取时发生异常: {errors}"
        assert all(r == 100 for r in results)


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self, cache: BridgesCache):
        result = cache.export()
        assert isinstance(result, dict)

    def test_export_contains_required_keys(self, cache: BridgesCache):
        result = cache.export()
        assert {"name", "path", "ttl_hours", "ttl_table", "hash_length"}.issubset(result)

    def test_export_name_matches_setting(self, cache: BridgesCache):
        assert cache.export()["name"] == cache._name

    def test_export_ttl_hours_matches_setting(self, cache: BridgesCache):
        assert cache.export()["ttl_hours"] == cache._ttl_hours

    def test_describe_returns_valid_json(self, cache: BridgesCache):
        result = cache.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_json_contains_required_keys(self, cache: BridgesCache):
        parsed = json.loads(cache.describe())
        assert "name" in parsed
        assert "path" in parsed
        assert "ttl_hours" in parsed


# ──────────────────────────────────────────────────────────────────────────────
# TestRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_does_not_raise(self, cache: BridgesCache):
        cache.refresh()

    def test_refresh_reconnects(self, cache: BridgesCache):
        cache.refresh()
        assert cache.conn is not None

    def test_refresh_retains_valid_data(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        cache.refresh()
        assert cache.check("k1") is True

    def test_refresh_removes_expired_entries(self, cache: BridgesCache):
        cache.write("k1", _SAMPLE_DF)
        identifier = cache.resolve_identifier("k1")
        _force_expire(cache, identifier)
        cache.refresh()
        assert cache.check("k1") is False


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_module_bridges_cache_is_bridges_cache(self):
        assert isinstance(ModuleBridgesCache, BridgesCache)

    def test_module_bridges_cache_has_connection(self):
        assert ModuleBridgesCache.conn is not None

    def test_module_bridges_cache_export_returns_dict(self):
        assert isinstance(ModuleBridgesCache.export(), dict)
