from __future__ import annotations

import duckdb
import pytest

from app.internal.model.dra import DRAMount, DRARejectedError
from app.service.node.dra.guard import RESERVED_SCHEMAS, DRAGuard


@pytest.fixture
def conn():
    _con = duckdb.connect(":memory:")
    yield _con
    _con.close()


def _file_mount(scope: str, pattern: str | None = None, **overrides) -> DRAMount:
    _kwargs = {"scheme": "file", "scope": scope, "pattern": pattern or scope + "*.parquet"}
    _kwargs.update(overrides)
    return DRAMount(**_kwargs)


def _s3_mount(scope: str = "s3://bkt/ds/", pattern: str | None = None, **overrides) -> DRAMount:
    _kwargs = {
        "scheme": "s3",
        "scope": scope,
        "pattern": pattern or scope + "*.parquet",
        "endpoint": "oss.example.com",
        "region": "cn-hangzhou",
        "url_style": "vhost",
    }
    _kwargs.update(overrides)
    return DRAMount(**_kwargs)


class TestCheckStatement:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 1",
            "select 1;",
            "WITH t AS (SELECT 1 AS a) SELECT * FROM t",
            "SELECT 1 UNION ALL SELECT 2",
        ],
    )
    def test_select_is_accepted(self, conn, sql):
        DRAGuard.check_statement(conn, sql)

    @pytest.mark.parametrize("sql", ["", "   ", "\n\t"])
    def test_empty_statement_is_rejected(self, conn, sql):
        with pytest.raises(DRARejectedError, match="empty statement"):
            DRAGuard.check_statement(conn, sql)

    @pytest.mark.parametrize("sql", [None, 1, b"SELECT 1"])
    def test_non_string_is_rejected(self, conn, sql):
        with pytest.raises(DRARejectedError, match="empty statement"):
            DRAGuard.check_statement(conn, sql)

    def test_unparsable_statement_is_rejected(self, conn):
        with pytest.raises(DRARejectedError, match="cannot parse"):
            DRAGuard.check_statement(conn, "SELEC 1 FROM")

    def test_multiple_statements_are_rejected(self, conn):
        with pytest.raises(DRARejectedError, match="exactly one statement"):
            DRAGuard.check_statement(conn, "SELECT 1; SELECT 2")

    @pytest.mark.parametrize(
        "sql",
        [
            "CREATE TABLE t (a INT)",
            "INSERT INTO t VALUES (1)",
            "DROP TABLE t",
            "SET threads=1",
            "COPY (SELECT 1) TO '/tmp/x.csv'",
            "ATTACH ':memory:' AS other",
            "INSTALL httpfs",
            "CALL pragma_version()",
        ],
    )
    def test_non_select_is_rejected(self, conn, sql):
        with pytest.raises(DRARejectedError):
            DRAGuard.check_statement(conn, sql)

    def test_select_followed_by_write_is_rejected(self, conn):
        with pytest.raises(DRARejectedError, match="exactly one statement"):
            DRAGuard.check_statement(conn, "SELECT 1; DROP TABLE t")


class TestCheckIdentifier:
    @pytest.mark.parametrize("value", ["a", "_", "orders", "orders_2024", "_private", "a" * 63])
    def test_valid_identifier_is_returned(self, value):
        assert DRAGuard.check_identifier(value, "name") == value

    @pytest.mark.parametrize(
        "value",
        ["", "1abc", "Orders", "a-b", "a b", "a.b", 'a"b', "a;b", "a" * 64, "名字", "a\n"],
    )
    def test_invalid_identifier_is_rejected(self, value):
        with pytest.raises(DRARejectedError, match="invalid name"):
            DRAGuard.check_identifier(value, "name")

    @pytest.mark.parametrize("value", [None, 1, ["a"]])
    def test_non_string_is_rejected(self, value):
        with pytest.raises(DRARejectedError):
            DRAGuard.check_identifier(value, "name")

    def test_message_mentions_what(self):
        with pytest.raises(DRARejectedError, match="invalid partition key"):
            DRAGuard.check_identifier("Bad", "partition key")


class TestSplitDatasetName:
    def test_valid_name_is_split(self):
        assert DRAGuard.split_dataset_name("sales.orders") == ("sales", "orders")

    @pytest.mark.parametrize("name", ["orders", "a.b.c", "", ".", "a.", ".b"])
    def test_wrong_shape_is_rejected(self, name):
        with pytest.raises(DRARejectedError):
            DRAGuard.split_dataset_name(name)

    @pytest.mark.parametrize("name", [None, 1, ["a", "b"]])
    def test_non_string_is_rejected(self, name):
        with pytest.raises(DRARejectedError, match="must be"):
            DRAGuard.split_dataset_name(name)

    @pytest.mark.parametrize("name", ["Sales.orders", "sales.Orders", 'sa"les.orders'])
    def test_invalid_part_is_rejected(self, name):
        with pytest.raises(DRARejectedError, match="invalid"):
            DRAGuard.split_dataset_name(name)

    @pytest.mark.parametrize("schema", sorted(RESERVED_SCHEMAS))
    def test_reserved_source_is_rejected(self, schema):
        with pytest.raises(DRARejectedError, match="reserved"):
            DRAGuard.split_dataset_name(f"{schema}.orders")

    def test_reserved_name_as_dataset_is_allowed(self):
        assert DRAGuard.split_dataset_name("sales.main") == ("sales", "main")


class TestCheckMountFile:
    def test_returns_resolved_scope_and_glob(self, tmp_path):
        _root = tmp_path.resolve()
        _scope = str(_root) + "/"
        _mount = _file_mount(_scope, _scope + "year=*/*.parquet", partitions=["year"])
        _out_scope, _out_glob = DRAGuard.check_mount(_mount)
        assert _out_scope == str(_root)
        assert _out_glob == str(_root / "year=*" / "*.parquet")

    def test_fixed_prefix_inside_scope_is_kept(self, tmp_path):
        _root = tmp_path.resolve()
        _scope = str(_root) + "/"
        _mount = _file_mount(_scope, _scope + "sub/dir/*.parquet")
        _, _out_glob = DRAGuard.check_mount(_mount)
        assert _out_glob == str(_root / "sub" / "dir" / "*.parquet")

    def test_pattern_without_glob_is_accepted(self, tmp_path):
        _root = tmp_path.resolve()
        _scope = str(_root) + "/"
        _, _out_glob = DRAGuard.check_mount(_file_mount(_scope, _scope + "one.parquet"))
        assert _out_glob == str(_root / "one.parquet")

    @pytest.mark.parametrize("partitions", [["Year"], ["a-b"], ["1a"], [""]])
    def test_invalid_partition_key_is_rejected(self, tmp_path, partitions):
        _scope = str(tmp_path.resolve()) + "/"
        with pytest.raises(DRARejectedError, match="partition key"):
            DRAGuard.check_mount(_file_mount(_scope, partitions=partitions))

    @pytest.mark.parametrize("bad", ["'", '"', "\\", "\x00", "\n"])
    def test_bad_characters_are_rejected(self, tmp_path, bad):
        _scope = str(tmp_path.resolve()) + "/"
        _mount = _file_mount(_scope, _scope + f"a{bad}b/*.parquet")
        with pytest.raises(DRARejectedError, match="invalid characters"):
            DRAGuard.check_mount(_mount)

    def test_relative_paths_are_rejected(self):
        _mount = _file_mount("data/", "data/*.parquet")
        with pytest.raises(DRARejectedError, match="absolute"):
            DRAGuard.check_mount(_mount)

    def test_parent_traversal_is_rejected(self, tmp_path):
        _scope = str(tmp_path.resolve()) + "/"
        _mount = _file_mount(_scope, _scope + "../other/*.parquet")
        with pytest.raises(DRARejectedError, match=r"'\.\.'"):
            DRAGuard.check_mount(_mount)

    def test_symlink_escaping_scope_is_rejected(self, tmp_path):
        _scope_dir = tmp_path / "scope"
        _outside = tmp_path / "outside"
        _scope_dir.mkdir()
        _outside.mkdir()
        (_scope_dir / "link").symlink_to(_outside, target_is_directory=True)
        _scope = str(_scope_dir.resolve()) + "/"
        _mount = _file_mount(_scope, _scope + "link/*.parquet")
        with pytest.raises(DRARejectedError, match="outside the scope"):
            DRAGuard.check_mount(_mount)

    def test_unsupported_scheme_is_rejected(self, tmp_path):
        _scope = str(tmp_path.resolve()) + "/"
        _mount = _file_mount(_scope).model_copy(update={"scheme": "gcs"})
        with pytest.raises(DRARejectedError, match="not supported"):
            DRAGuard.check_mount(_mount)


class TestCheckMountS3:
    def test_valid_mount_is_returned_as_is(self):
        _mount = _s3_mount("s3://bkt/ds/", "s3://bkt/ds/year=*/*.parquet")
        assert DRAGuard.check_mount(_mount) == ("s3://bkt/ds/", "s3://bkt/ds/year=*/*.parquet")

    def test_bucket_root_scope_is_accepted(self):
        _mount = _s3_mount("s3://bkt/", "s3://bkt/*.parquet")
        assert DRAGuard.check_mount(_mount) == ("s3://bkt/", "s3://bkt/*.parquet")

    def test_scope_without_bucket_is_rejected(self):
        _mount = _s3_mount("s3://", "s3://*.parquet")
        with pytest.raises(DRARejectedError, match="s3://"):
            DRAGuard.check_mount(_mount)

    def test_non_s3_prefix_is_rejected(self):
        _mount = _s3_mount("http://bkt/ds/", "http://bkt/ds/*.parquet")
        with pytest.raises(DRARejectedError, match="s3://"):
            DRAGuard.check_mount(_mount)

    def test_parent_traversal_is_rejected(self):
        _mount = _s3_mount("s3://bkt/ds/", "s3://bkt/ds/../other/*.parquet")
        with pytest.raises(DRARejectedError, match=r"'\.\.'"):
            DRAGuard.check_mount(_mount)

    @pytest.mark.parametrize("bad", ["'", '"', "\\"])
    def test_bad_characters_are_rejected(self, bad):
        _mount = _s3_mount("s3://bkt/ds/", f"s3://bkt/ds/a{bad}b/*.parquet")
        with pytest.raises(DRARejectedError, match="invalid characters"):
            DRAGuard.check_mount(_mount)

    def test_invalid_partition_key_is_rejected(self):
        with pytest.raises(DRARejectedError, match="partition key"):
            DRAGuard.check_mount(_s3_mount(partitions=["Bad-Key"]))


class TestStringifySql:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("abc", "'abc'"),
            ("", "''"),
            ("it's", "'it''s'"),
            ("''", "''''''"),
            ("a;--b", "'a;--b'"),
        ],
    )
    def test_value_is_quoted_and_escaped(self, value, expected):
        assert DRAGuard.stringify_sql(value) == expected

    def test_result_round_trips_through_engine(self, conn):
        _value = "x'; DROP TABLE t; --"
        _row = conn.execute(f"SELECT {DRAGuard.stringify_sql(_value)}").fetchone()
        assert _row == (_value,)
