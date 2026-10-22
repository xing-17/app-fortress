from __future__ import annotations

import io
import socket
import time

import duckdb
import pytest

boto3 = pytest.importorskip("boto3")
moto_server = pytest.importorskip("moto.server")

from app.resource.asset import DRAMount  # noqa: E402
from app.service.node.dra import DRALimits, DRASession  # noqa: E402
from app.service.node.dra.errors import DRAQueryError, DRARejectedError  # noqa: E402

_KEY_ID = "AKIATESTKEYID"
_SECRET = "test-secret-value-9f3a"
_TOKEN = "test-session-token-7c1d"


def _free_port() -> int:
    with socket.socket() as _sock:
        _sock.bind(("127.0.0.1", 0))
        return _sock.getsockname()[1]


def _parquet_bytes(select_sql: str) -> bytes:
    _con = duckdb.connect(":memory:")
    try:
        _buf = _con.execute(f"SELECT * FROM ({select_sql})").to_arrow_table()
    finally:
        _con.close()
    import pyarrow.parquet as pq

    _out = io.BytesIO()
    pq.write_table(_buf, _out)
    return _out.getvalue()


@pytest.fixture(scope="module")
def s3_endpoint():
    _port = _free_port()
    _server = moto_server.ThreadedMotoServer(ip_address="127.0.0.1", port=_port, verbose=False)
    _server.start()
    _endpoint = f"127.0.0.1:{_port}"
    _client = boto3.client(
        "s3",
        endpoint_url=f"http://{_endpoint}",
        aws_access_key_id=_KEY_ID,
        aws_secret_access_key=_SECRET,
        region_name="us-east-1",
    )
    for _ in range(50):
        try:
            _client.list_buckets()
            break
        except Exception:
            time.sleep(0.1)

    for _bucket in ("bkt-a", "bkt-b", "bkt-pub"):
        _client.create_bucket(Bucket=_bucket)
    _put = _client.put_object
    _put(Bucket="bkt-a", Key="ds/year=2023/a.parquet", Body=_parquet_bytes("SELECT 1 AS id, 'x' AS tag"))
    _put(Bucket="bkt-a", Key="ds/year=2024/a.parquet", Body=_parquet_bytes("SELECT 2 AS id, 'y' AS tag"))
    _put(Bucket="bkt-a", Key="ds/year=2024/b.parquet", Body=_parquet_bytes("SELECT 3 AS id, 'z' AS tag"))
    _put(Bucket="bkt-a", Key="other/o.parquet", Body=_parquet_bytes("SELECT 99 AS id"))
    _put(Bucket="bkt-b", Key="ds/b.parquet", Body=_parquet_bytes("SELECT 77 AS id"))
    _client.put_object(
        Bucket="bkt-pub",
        Key="ds/p.parquet",
        Body=_parquet_bytes("SELECT 5 AS id"),
        ACL="public-read",
    )
    yield _endpoint
    _server.stop()


def _mount(endpoint: str, **overrides) -> DRAMount:
    _kwargs = {
        "scheme": "s3",
        "scope": "s3://bkt-a/ds/",
        "pattern": "s3://bkt-a/ds/*/*.parquet",
        "partitions": ["year"],
        "endpoint": endpoint,
        "region": "us-east-1",
        "url_style": "path",
        "use_ssl": False,
        "key_id": _KEY_ID,
        "secret": _SECRET,
        "session_token": _TOKEN,
    }
    _kwargs.update(overrides)
    return DRAMount(**_kwargs)


@pytest.fixture
def session(s3_endpoint):
    _session = DRASession({"cloud.ds": _mount(s3_endpoint)})
    yield _session
    _session.close()


class TestDRASessionS3Read:
    def test_query_reads_across_files_and_partitions(self, session):
        result = session.query("SELECT id, tag, year FROM cloud.ds ORDER BY id")
        assert result.rows == [[1, "x", "2023"], [2, "y", "2024"], [3, "z", "2024"]]

    def test_partition_filter(self, session):
        result = session.query("SELECT count(*) FROM cloud.ds WHERE year = '2024'")
        assert result.rows == [[2]]

    def test_definition_reports_partitions(self, session):
        _definition = session.definition("cloud.ds")
        assert _definition.partitions == ["year"]
        assert {c.name for c in _definition.columns} == {"id", "tag", "year"}

    def test_glob_inside_scope_is_allowed(self, session):
        result = session.query("SELECT count(*) FROM glob('s3://bkt-a/ds/*/*.parquet')")
        assert result.rows == [[3]]

    def test_anonymous_mount_reads_public_data(self, s3_endpoint):
        _mount_obj = _mount(
            s3_endpoint,
            scope="s3://bkt-pub/ds/",
            pattern="s3://bkt-pub/ds/*.parquet",
            partitions=[],
            key_id=None,
            secret=None,
            session_token=None,
        )
        with DRASession({"cloud.ds": _mount_obj}) as _session:
            assert _session.query("SELECT id FROM cloud.ds").rows == [[5]]

    def test_anonymous_mount_cannot_read_private_data(self, s3_endpoint):
        _mount_obj = _mount(s3_endpoint, key_id=None, secret=None, session_token=None)
        with pytest.raises(DRAQueryError):
            DRASession({"cloud.ds": _mount_obj})

    def test_max_rows_applies_to_remote_data(self, s3_endpoint):
        _limits = DRALimits(max_rows=2)
        with DRASession({"cloud.ds": _mount(s3_endpoint)}, _limits) as _session:
            result = _session.query("SELECT id FROM cloud.ds ORDER BY id")
        assert result.rows == [[1], [2]]
        assert result.truncated_by == "rows"


class TestDRASessionS3Sandbox:
    def test_other_prefix_of_same_bucket_is_rejected(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT * FROM read_parquet('s3://bkt-a/other/o.parquet')")

    def test_other_bucket_is_rejected(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT * FROM read_parquet('s3://bkt-b/ds/b.parquet')")

    def test_glob_outside_prefix_is_rejected(self, session):
        with pytest.raises(DRAQueryError):
            session.query("SELECT * FROM glob('s3://bkt-a/other/*')")

    def test_plain_http_is_rejected(self, s3_endpoint, session):
        with pytest.raises(DRAQueryError):
            session.query(f"SELECT * FROM read_parquet('http://{s3_endpoint}/bkt-a/other/o.parquet')")

    def test_local_file_is_rejected(self, tmp_path, session):
        _file = tmp_path / "plain.csv"
        _file.write_text("a\n1\n")
        with pytest.raises(DRAQueryError):
            session.query(f"SELECT * FROM read_csv('{_file}')")

    @pytest.mark.parametrize(
        "sql",
        [
            "SET enable_external_access=true",
            "ATTACH ':memory:' AS other",
            "CREATE SECRET evil (TYPE s3, KEY_ID 'x', SECRET 'y')",
            "DROP SECRET dra_s3_0",
            "INSTALL httpfs",
        ],
    )
    def test_non_select_is_rejected(self, session, sql):
        with pytest.raises(DRARejectedError):
            session.query(sql)

    def test_configuration_is_locked_after_secrets(self, session):
        with pytest.raises(duckdb.Error):
            session._con.execute("SET allowed_directories=['s3://bkt-b/']")

    def test_secret_can_be_replaced_after_lock(self, s3_endpoint):
        with DRASession({"cloud.ds": _mount(s3_endpoint)}) as _session:
            _session._con.execute(
                DRASession._secret_sql("dra_s3_0", _mount(s3_endpoint)).replace("CREATE", "CREATE OR REPLACE", 1)
            )
            assert _session.query("SELECT count(*) FROM cloud.ds").rows == [[3]]


class TestDRASessionS3Secrets:
    def test_secret_values_are_redacted_in_engine(self, session):
        _rows = session._con.execute("SELECT * FROM duckdb_secrets()").fetchall()
        assert _rows
        _text = repr(_rows)
        assert _SECRET not in _text
        assert _TOKEN not in _text

    def test_secret_not_in_mount_repr(self, s3_endpoint):
        _mount_obj = _mount(s3_endpoint)
        assert _SECRET not in repr(_mount_obj)
        assert _TOKEN not in repr(_mount_obj)

    def test_secret_not_in_query_error(self, session):
        with pytest.raises(DRAQueryError) as _info:
            session.query("SELECT * FROM read_parquet('s3://bkt-b/ds/b.parquet')")
        assert _SECRET not in str(_info.value)
        assert _TOKEN not in str(_info.value)

    def test_unreachable_endpoint_error_hides_secret(self):
        _mount_obj = _mount(f"127.0.0.1:{_free_port()}")
        with pytest.raises(DRAQueryError) as _info:
            DRASession({"cloud.ds": _mount_obj})
        assert _SECRET not in str(_info.value)
        assert _TOKEN not in str(_info.value)


class TestDRASessionS3Refresh:
    def test_same_mount_is_accepted(self, session, s3_endpoint):
        session.refresh({"cloud.ds": _mount(s3_endpoint)})

    def test_changed_scope_is_rejected(self, session, s3_endpoint):
        _other = _mount(s3_endpoint, scope="s3://bkt-b/ds/", pattern="s3://bkt-b/ds/*.parquet", partitions=[])
        with pytest.raises(DRARejectedError, match="mounts changed"):
            session.refresh({"cloud.ds": _other})
