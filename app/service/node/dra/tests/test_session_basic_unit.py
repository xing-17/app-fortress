from __future__ import annotations

import threading
from pathlib import Path

import duckdb
import pytest

from app.service.node.dra import (
    DRADataResult,
    DRADefinitionResult,
    DRALimits,
    DRAMount,
    DRASession,
)
from app.service.node.dra.errors import (
    DRAError,
    DRAQueryError,
    DRAQueryTimeoutError,  # noqa: E402
    DRARejectedError,
)


def _write_parquet(path: Path, select_sql: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _con = duckdb.connect(":memory:")
    try:
        _con.execute(f"COPY ({select_sql}) TO '{path}' (FORMAT parquet)")
    finally:
        _con.close()
    return path


def _mount_of(root: Path, glob: str = "*.parquet", **overrides) -> DRAMount:
    _scope = str(root.resolve()) + "/"
    _kwargs = {"scheme": "file", "scope": _scope, "pattern": _scope + glob}
    _kwargs.update(overrides)
    return DRAMount(**_kwargs)


@pytest.fixture
def orders_dir(tmp_path):
    _dir = tmp_path / "orders"
    _write_parquet(
        _dir / "part.parquet",
        "SELECT i AS id, 'n' || i AS name, CASE WHEN i = 3 THEN NULL ELSE i * 1.5 END AS amount FROM range(1, 6) t(i)",
    )
    return _dir


@pytest.fixture
def session(orders_dir):
    _session = DRASession({"sales.orders": _mount_of(orders_dir)})
    yield _session
    _session.close()


class TestDRASessionInit:
    def test_empty_mounts_are_rejected(self):
        with pytest.raises(DRARejectedError, match="at least one mount"):
            DRASession({})

    @pytest.mark.parametrize("name", ["orders", "Sales.orders", "main.orders", "a.b.c"])
    def test_invalid_dataset_name_is_rejected(self, orders_dir, name):
        with pytest.raises(DRARejectedError):
            DRASession({name: _mount_of(orders_dir)})

    def test_pattern_escaping_scope_is_rejected(self, tmp_path, orders_dir):
        _scope = str(orders_dir.resolve()) + "/"
        _mount = DRAMount(scope=_scope, pattern=_scope + "../*.parquet")
        with pytest.raises(DRARejectedError):
            DRASession({"sales.orders": _mount})

    def test_unmatched_glob_is_a_query_error(self, tmp_path):
        _empty = tmp_path / "empty"
        _empty.mkdir()
        with pytest.raises(DRAQueryError, match="cannot mount sales.orders"):
            DRASession({"sales.orders": _mount_of(_empty)})

    def test_one_bad_mount_rejects_whole_session(self, tmp_path, orders_dir):
        _mounts = {
            "sales.orders": _mount_of(orders_dir),
            "sales.missing": _mount_of(tmp_path / "missing"),
        }
        with pytest.raises(DRAError):
            DRASession(_mounts)

    def test_default_limits_are_used(self, session):
        assert session._limits == DRALimits()

    def test_custom_limits_are_used(self, orders_dir):
        _limits = DRALimits(max_rows=2)
        with DRASession({"sales.orders": _mount_of(orders_dir)}, _limits) as _session:
            assert _session._limits is _limits


class TestDRASessionQuery:
    def test_select_returns_columns_types_and_rows(self, session):
        result = session.query("SELECT id, name FROM sales.orders ORDER BY id")
        assert isinstance(result, DRADataResult)
        assert result.columns == ["id", "name"]
        assert result.types == ["BIGINT", "VARCHAR"]
        assert result.rows == [[1, "n1"], [2, "n2"], [3, "n3"], [4, "n4"], [5, "n5"]]
        assert result.truncated is False
        assert result.truncated_by is None
        assert result.elapsed_ms >= 0

    def test_null_values_are_kept(self, session):
        result = session.query("SELECT amount FROM sales.orders WHERE id = 3")
        assert result.rows == [[None]]

    def test_aggregate_query(self, session):
        result = session.query("SELECT count(*) AS n, sum(id) AS total FROM sales.orders")
        assert result.columns == ["n", "total"]
        assert result.rows == [[5, 15]]

    def test_sum_of_integers_is_an_int_not_a_decimal(self, session):
        result = session.query("SELECT sum(id) AS total FROM sales.orders")
        assert result.types == ["HUGEINT"]
        assert type(result.rows[0][0]) is int

    def test_huge_int_keeps_nulls_and_big_values(self, session):
        result = session.query(
            "SELECT x FROM (VALUES (NULL::HUGEINT), (170141183460469231731687303715884105727::HUGEINT)) t(x)"
        )
        assert result.rows == [[None], [2**127 - 1]]
        assert type(result.rows[1][0]) is int

    def test_decimal_column_stays_a_decimal(self, session):
        result = session.query("SELECT sum(amount) AS total FROM sales.orders")
        assert result.types[0].startswith("DECIMAL")
        assert not isinstance(result.rows[0][0], int)

    def test_empty_result_keeps_columns(self, session):
        result = session.query("SELECT id, name FROM sales.orders WHERE id > 100")
        assert result.columns == ["id", "name"]
        assert result.rows == []
        assert result.truncated is False

    def test_with_clause_is_allowed(self, session):
        result = session.query("WITH t AS (SELECT id FROM sales.orders) SELECT count(*) FROM t")
        assert result.rows == [[5]]

    def test_trailing_semicolon_is_allowed(self, session):
        assert session.query("SELECT 1 AS one;").rows == [[1]]

    def test_multiple_datasets_can_be_joined(self, tmp_path, orders_dir):
        _users = tmp_path / "users"
        _write_parquet(_users / "u.parquet", "SELECT i AS id, 'u' || i AS user FROM range(1, 3) t(i)")
        _mounts = {"sales.orders": _mount_of(orders_dir), "crm.users": _mount_of(_users)}
        with DRASession(_mounts) as _session:
            result = _session.query(
                "SELECT o.id, u.user FROM sales.orders o JOIN crm.users u ON o.id = u.id ORDER BY o.id"
            )
        assert result.rows == [[1, "u1"], [2, "u2"]]

    def test_multiple_files_are_unioned_by_name(self, tmp_path):
        _dir = tmp_path / "multi"
        _write_parquet(_dir / "a.parquet", "SELECT 1 AS id, 'x' AS tag")
        _write_parquet(_dir / "b.parquet", "SELECT 2 AS id")
        with DRASession({"s.d": _mount_of(_dir)}) as _session:
            result = _session.query("SELECT id, tag FROM s.d ORDER BY id")
        assert result.rows == [[1, "x"], [2, None]]

    @pytest.mark.parametrize(
        "sql",
        [
            "CREATE TABLE t (a INT)",
            "DROP VIEW sales.orders",
            "INSERT INTO sales.orders VALUES (1, 'x', 1.0)",
            "SET enable_external_access=true",
            "ATTACH ':memory:' AS other",
            "COPY sales.orders TO 'out.csv'",
            "",
            "SELECT 1; SELECT 2",
        ],
    )
    def test_rejected_statements(self, session, sql):
        with pytest.raises(DRARejectedError):
            session.query(sql)

    def test_syntax_error_is_rejected(self, session):
        with pytest.raises(DRARejectedError):
            session.query("SELECT FROM WHERE")

    def test_unknown_table_is_a_query_error(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT * FROM sales.nope")

    def test_runtime_error_is_a_query_error(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT CAST('abc' AS INTEGER)")

    def test_session_is_reusable_after_error(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT * FROM sales.nope")
        assert session.query("SELECT 1").rows == [[1]]


class TestDRASessionSandbox:
    def test_file_outside_scope_cannot_be_read(self, tmp_path, session):
        _secret = _write_parquet(tmp_path / "secret" / "s.parquet", "SELECT 42 AS v")
        with pytest.raises(DRAQueryError):
            session.query(f"SELECT * FROM read_parquet('{_secret}')")

    def test_text_file_outside_scope_cannot_be_read(self, tmp_path, session):
        _file = tmp_path / "plain.csv"
        _file.write_text("a\n1\n")
        with pytest.raises(DRAQueryError):
            session.query(f"SELECT * FROM read_csv('{_file}')")

    def test_glob_outside_scope_cannot_list_files(self, tmp_path, session):
        with pytest.raises(DRAQueryError):
            session.query(f"SELECT * FROM glob('{tmp_path}/*')")

    def test_configuration_is_locked(self, session):
        with pytest.raises(duckdb.Error):
            session._con.execute("SET enable_external_access=true")

    def test_external_access_is_disabled(self, session):
        _value = session._con.execute(
            "SELECT value FROM duckdb_settings() WHERE name = 'enable_external_access'"
        ).fetchone()[0]
        assert _value == "false"

    def test_limits_are_applied_to_engine(self, orders_dir):
        _limits = DRALimits(threads=1, memory_limit_mb=64)
        with DRASession({"sales.orders": _mount_of(orders_dir)}, _limits) as _session:
            _threads = _session._con.execute("SELECT value FROM duckdb_settings() WHERE name = 'threads'").fetchone()[0]
        assert _threads == "1"


class TestDRASessionCaps:
    def test_max_rows_truncates(self, orders_dir):
        with DRASession({"sales.orders": _mount_of(orders_dir)}, DRALimits(max_rows=2)) as _session:
            result = _session.query("SELECT id FROM sales.orders ORDER BY id")
        assert result.rows == [[1], [2]]
        assert result.truncated is True
        assert result.truncated_by == "rows"

    def test_exactly_max_rows_is_not_truncated(self, orders_dir):
        with DRASession({"sales.orders": _mount_of(orders_dir)}, DRALimits(max_rows=5)) as _session:
            result = _session.query("SELECT id FROM sales.orders")
        assert len(result.rows) == 5
        assert result.truncated is False

    def test_max_rows_across_batches(self, orders_dir):
        with DRASession({"sales.orders": _mount_of(orders_dir)}, DRALimits(max_rows=2500)) as _session:
            result = _session.query("SELECT i FROM range(5000) t(i)")
        assert len(result.rows) == 2500
        assert result.truncated_by == "rows"
        assert result.rows[0] == [0]
        assert result.rows[-1] == [2499]

    def test_max_result_mb_truncates(self, orders_dir):
        _limits = DRALimits(max_result_mb=0.01)
        with DRASession({"sales.orders": _mount_of(orders_dir)}, _limits) as _session:
            result = _session.query("SELECT i, repeat('x', 100) AS pad FROM range(5000) t(i)")
        assert result.truncated is True
        assert result.truncated_by == "size"
        assert 0 < len(result.rows) < 5000

    def test_timeout_raises(self, orders_dir):
        _limits = DRALimits(timeout_seconds=0.2)
        with DRASession({"sales.orders": _mount_of(orders_dir)}, _limits) as _session:
            with pytest.raises(DRAQueryTimeoutError, match="exceeded"):
                _session.query("SELECT count(*) FROM range(100000000000) a")

    def test_session_is_usable_after_timeout(self, orders_dir):
        _limits = DRALimits(timeout_seconds=0.2)
        with DRASession({"sales.orders": _mount_of(orders_dir)}, _limits) as _session:
            with pytest.raises(DRAQueryTimeoutError):
                _session.query("SELECT count(*) FROM range(100000000000) a")
            assert _session.query("SELECT 1").rows == [[1]]


class TestDRASessionDefinition:
    def test_columns_and_types(self, session):
        result = session.definition("sales.orders")
        assert isinstance(result, DRADefinitionResult)
        assert result.dataset == "sales.orders"
        assert [c.name for c in result.columns] == ["id", "name", "amount"]
        assert [c.type for c in result.columns[:2]] == ["BIGINT", "VARCHAR"]
        assert result.partitions == []

    def test_nullable_flag(self, tmp_path):
        _dir = tmp_path / "n"
        _write_parquet(_dir / "a.parquet", "SELECT 1 AS id")
        with DRASession({"s.d": _mount_of(_dir)}) as _session:
            result = _session.definition("s.d")
        assert result.columns[0].nullable is True

    def test_unknown_dataset_is_rejected(self, session):
        with pytest.raises(DRAError, match="unknown dataset"):
            session.definition("sales.nope")

    @pytest.mark.parametrize("name", ["orders", "Sales.orders", "main.orders"])
    def test_invalid_name_is_rejected(self, session, name):
        with pytest.raises(DRARejectedError):
            session.definition(name)

    def test_vanished_file_is_a_query_error(self, session, orders_dir):
        (orders_dir / "part.parquet").unlink()
        with pytest.raises(DRAQueryError, match="cannot describe"):
            session.definition("sales.orders")

    def test_partitions_are_reported_and_queryable(self, tmp_path):
        _dir = tmp_path / "hive"
        _write_parquet(_dir / "year=2023" / "a.parquet", "SELECT 1 AS id")
        _write_parquet(_dir / "year=2024" / "a.parquet", "SELECT 2 AS id")
        _mount = _mount_of(_dir, "year=*/*.parquet", partitions=["year"])
        with DRASession({"s.d": _mount}) as _session:
            _definition = _session.definition("s.d")
            result = _session.query("SELECT id, year FROM s.d ORDER BY id")
        assert _definition.partitions == ["year"]
        assert "year" in [c.name for c in _definition.columns]
        assert result.rows == [[1, "2023"], [2, "2024"]]

    def test_returned_partitions_are_a_copy(self, tmp_path):
        _dir = tmp_path / "hive"
        _write_parquet(_dir / "year=2023" / "a.parquet", "SELECT 1 AS id")
        _mount = _mount_of(_dir, "year=*/*.parquet", partitions=["year"])
        with DRASession({"s.d": _mount}) as _session:
            _session.definition("s.d").partitions.append("x")
            assert _session.definition("s.d").partitions == ["year"]


class TestDRASessionRefresh:
    def test_same_mounts_are_accepted(self, session, orders_dir):
        session.refresh({"sales.orders": _mount_of(orders_dir)})

    def test_added_mount_is_rejected(self, session, orders_dir, tmp_path):
        _other = tmp_path / "other"
        _other.mkdir()
        _mounts = {"sales.orders": _mount_of(orders_dir), "sales.other": _mount_of(_other)}
        with pytest.raises(DRARejectedError, match="mounts changed"):
            session.refresh(_mounts)

    def test_removed_mount_is_rejected(self, session):
        with pytest.raises(DRARejectedError, match="mounts changed"):
            session.refresh({})

    def test_changed_scope_is_rejected(self, session, tmp_path):
        _other = tmp_path / "other"
        _other.mkdir()
        with pytest.raises(DRARejectedError, match="mounts changed"):
            session.refresh({"sales.orders": _mount_of(_other)})

    def test_invalid_mount_is_rejected(self, session, orders_dir):
        _scope = str(orders_dir.resolve()) + "/"
        _mount = DRAMount(scope=_scope, pattern=_scope + "../*.parquet")
        with pytest.raises(DRARejectedError):
            session.refresh({"sales.orders": _mount})


class TestDRASessionLifecycle:
    def test_query_after_close_raises(self, orders_dir):
        _session = DRASession({"sales.orders": _mount_of(orders_dir)})
        _session.close()
        with pytest.raises(DRAError, match="closed"):
            _session.query("SELECT 1")

    def test_definition_after_close_raises(self, orders_dir):
        _session = DRASession({"sales.orders": _mount_of(orders_dir)})
        _session.close()
        with pytest.raises(DRAError, match="closed"):
            _session.definition("sales.orders")

    def test_close_is_idempotent(self, orders_dir):
        _session = DRASession({"sales.orders": _mount_of(orders_dir)})
        _session.close()
        _session.close()

    def test_context_manager_closes(self, orders_dir):
        with DRASession({"sales.orders": _mount_of(orders_dir)}) as _session:
            assert _session.query("SELECT 1").rows == [[1]]
        with pytest.raises(DRAError, match="closed"):
            _session.query("SELECT 1")

    def test_context_manager_does_not_swallow_exceptions(self, orders_dir):
        with pytest.raises(ValueError):
            with DRASession({"sales.orders": _mount_of(orders_dir)}):
                raise ValueError("boom")

    def test_concurrent_queries(self, session):
        _results: list[int] = []
        _errors: list[BaseException] = []

        def _run() -> None:
            try:
                _results.append(session.query("SELECT count(*) FROM sales.orders").rows[0][0])
            except BaseException as e:
                _errors.append(e)

        _threads = [threading.Thread(target=_run) for _ in range(8)]
        for _t in _threads:
            _t.start()
        for _t in _threads:
            _t.join()
        assert _errors == []
        assert _results == [5] * 8


class TestDRASessionSecretSql:
    def _s3(self, **overrides) -> DRAMount:
        _kwargs = {
            "scheme": "s3",
            "scope": "s3://bkt/ds/",
            "pattern": "s3://bkt/ds/*.parquet",
            "endpoint": "oss.example.com",
            "region": "cn-hangzhou",
            "url_style": "vhost",
        }
        _kwargs.update(overrides)
        return DRAMount(**_kwargs)

    def test_anonymous_secret(self):
        _sql = DRASession._secret_sql("dra_s3_0", self._s3())
        assert _sql.startswith("CREATE SECRET dra_s3_0 (TYPE s3, ")
        assert "ENDPOINT 'oss.example.com'" in _sql
        assert "REGION 'cn-hangzhou'" in _sql
        assert "URL_STYLE 'vhost'" in _sql
        assert "USE_SSL true" in _sql
        assert "SCOPE 's3://bkt/ds/'" in _sql
        assert "KEY_ID" not in _sql
        assert "SESSION_TOKEN" not in _sql

    def test_credentials_are_included(self):
        _sql = DRASession._secret_sql("n", self._s3(key_id="AK", secret="SK", session_token="TOK"))
        assert "KEY_ID 'AK'" in _sql
        assert "SECRET 'SK'" in _sql
        assert "SESSION_TOKEN 'TOK'" in _sql

    def test_use_ssl_false(self):
        _sql = DRASession._secret_sql("n", self._s3(use_ssl=False))
        assert "USE_SSL false" in _sql

    def test_values_are_escaped(self):
        _sql = DRASession._secret_sql("n", self._s3(key_id="A'K", secret="S'K"))
        assert "KEY_ID 'A''K'" in _sql
        assert "SECRET 'S''K'" in _sql
