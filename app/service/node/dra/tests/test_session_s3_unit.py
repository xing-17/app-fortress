from __future__ import annotations

import io
import socket
import threading
import time

import duckdb
import pytest

boto3 = pytest.importorskip("boto3")
moto_server = pytest.importorskip("moto.server")

from app.resource.asset import DRAMount  # noqa: E402
from app.service.node.dra import DRALimits, DRASession  # noqa: E402
from app.service.node.dra.errors import DRAError, DRAQueryError, DRARefreshError, DRARejectedError  # noqa: E402

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


class _SpyConnection:
    """Records the statements run on the engine, optionally fails the ones containing `fail_on`."""

    def __init__(self, con, fail_on: str | None = None):
        self._con = con
        self._fail_on = fail_on
        self.statements: list[str] = []

    def execute(self, sql, *args, **kwargs):
        self.statements.append(sql)
        if self._fail_on and self._fail_on in sql:
            raise duckdb.IOException(f"boom while running {sql}")
        return self._con.execute(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._con, name)


class TestDRASessionS3Refresh:
    def test_same_mount_is_accepted(self, session, s3_endpoint):
        session.refresh({"cloud.ds": _mount(s3_endpoint)})

    def test_changed_scope_is_rejected(self, session, s3_endpoint):
        _other = _mount(s3_endpoint, scope="s3://bkt-b/ds/", pattern="s3://bkt-b/ds/*.parquet", partitions=[])
        with pytest.raises(DRARejectedError, match="mounts changed"):
            session.refresh({"cloud.ds": _other})

    def test_session_reports_its_secrets(self, session):
        assert session.has_secrets is True
        assert session.names == ["cloud.ds"]

    def test_unchanged_credentials_run_nothing(self, session, s3_endpoint):
        _spy = _SpyConnection(session._con)
        session._con = _spy
        session.refresh({"cloud.ds": _mount(s3_endpoint)})
        assert _spy.statements == []

    def test_unchanged_credentials_still_count_as_refreshed(self, session, s3_endpoint):
        _before = session.refreshed_at
        session.refresh({"cloud.ds": _mount(s3_endpoint)})
        assert session.refreshed_at > _before

    def test_new_token_replaces_the_secret_once(self, session, s3_endpoint):
        _spy = _SpyConnection(session._con)
        session._con = _spy
        _new = _mount(s3_endpoint, session_token="rotated-token")
        session.refresh({"cloud.ds": _new})
        session.refresh({"cloud.ds": _new})
        assert len(_spy.statements) == 1
        assert _spy.statements[0].startswith("CREATE OR REPLACE SECRET dra_s3_0 ")
        assert "rotated-token" in _spy.statements[0]
        assert session.query("SELECT count(*) FROM cloud.ds").rows == [[3]]

    def test_replaced_secret_is_the_one_in_use(self, s3_endpoint):
        # The engine caches what it already read, so probe with objects it has not touched yet
        _client = boto3.client(
            "s3",
            endpoint_url=f"http://{s3_endpoint}",
            aws_access_key_id=_KEY_ID,
            aws_secret_access_key=_SECRET,
            region_name="us-east-1",
        )
        for _key in ("seed", "p1", "p2"):
            _client.put_object(Bucket="bkt-a", Key=f"probe/{_key}.parquet", Body=_parquet_bytes("SELECT 1 AS id"))

        def _probe_mount(**overrides) -> DRAMount:
            return _mount(
                s3_endpoint,
                scope="s3://bkt-a/probe/",
                pattern="s3://bkt-a/probe/*.parquet",
                partitions=[],
                **overrides,
            )

        with DRASession({"cloud.probe": _probe_mount()}) as _session:
            _session.refresh({"cloud.probe": _probe_mount(key_id=None, secret=None, session_token=None)})
            with pytest.raises(DRAQueryError):
                _session.query("SELECT id FROM read_parquet('s3://bkt-a/probe/p1.parquet')")
            _session.refresh({"cloud.probe": _probe_mount()})
            assert _session.query("SELECT id FROM read_parquet('s3://bkt-a/probe/p2.parquet')").rows == [[1]]

    def test_secrets_stay_redacted_after_replacement(self, session, s3_endpoint):
        session.refresh({"cloud.ds": _mount(s3_endpoint, secret="rotated-secret", session_token="rotated-token")})
        _text = repr(session._con.execute("SELECT * FROM duckdb_secrets()").fetchall())
        assert "rotated-secret" not in _text
        assert "rotated-token" not in _text

    def test_failed_replacement_keeps_the_old_secret_and_hides_the_new_one(self, session, s3_endpoint):
        _digests = dict(session._digests)
        _before = session.refreshed_at
        session._con = _SpyConnection(session._con, fail_on="CREATE OR REPLACE")
        with pytest.raises(DRARefreshError) as _info:
            session.refresh({"cloud.ds": _mount(s3_endpoint, secret="rotated-secret")})

        assert "rotated-secret" not in str(_info.value)
        assert "boom" not in str(_info.value)
        assert _info.value.__cause__ is None
        assert _info.value.__suppress_context__ is True
        assert session._digests == _digests
        assert session.refreshed_at == _before
        # The next attempt is not skipped as unchanged
        session._con = session._con._con
        session.refresh({"cloud.ds": _mount(s3_endpoint, secret="rotated-secret")})
        assert session._digests != _digests
        assert session.query("SELECT count(*) FROM cloud.ds").rows == [[3]]

    def test_refresh_after_close_raises(self, s3_endpoint):
        _session = DRASession({"cloud.ds": _mount(s3_endpoint)})
        _session.close()
        with pytest.raises(DRAError, match="closed"):
            _session.refresh({"cloud.ds": _mount(s3_endpoint)})

    def test_refresh_during_queries_is_safe(self, session, s3_endpoint):
        _errors: list[BaseException] = []
        _stop = threading.Event()

        def _query() -> None:
            try:
                while not _stop.is_set():
                    assert session.query("SELECT count(*) FROM cloud.ds").rows == [[3]]
            except BaseException as e:
                _errors.append(e)

        _threads = [threading.Thread(target=_query) for _ in range(3)]
        for _t in _threads:
            _t.start()
        try:
            for _i in range(20):
                session.refresh({"cloud.ds": _mount(s3_endpoint, session_token=f"token-{_i}")})
        finally:
            _stop.set()
            for _t in _threads:
                _t.join()
        assert _errors == []
