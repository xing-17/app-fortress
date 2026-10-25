from __future__ import annotations

import pytest

from app.service.node.dra import DRARejectedError
from app.service.node.service.errors import NodeBusyError, NodeUnavailableError

from .conftest import HTML, JSON


def _column(name, complete=1.0, nulls=0):
    return {
        "name": name,
        "type": "DOUBLE",
        "complete_rate": complete,
        "null_count": nulls,
        "unique_count": 5,
        "duplicate_count": 1,
        "is_all_null": False,
        "is_constant": False,
        "is_unique": False,
    }


def _qualities():
    _first = {
        "height": 100,
        "width": 2,
        "complete_rows": 90,
        "duplicate_rows": 2,
        "created_at": 5.0,
        "columns": [_column("px", 0.9, 10), _column("vol")],
    }
    _clean = {**_first, "complete_rows": 100, "duplicate_rows": 0, "columns": [_column("px"), _column("vol")]}
    return [
        {"assetfile": {"name": "a", "partitions": {"date": "d1"}, "modified_at": 3.0}, "quality": _first},
        {"assetfile": {"name": "b", "partitions": {"date": "d2"}, "modified_at": 2.0}, "quality": None},
        {"assetfile": {"name": "c", "partitions": {"date": "d3"}, "modified_at": 1.0}, "quality": _clean},
    ]


class TestSidebar:
    def test_home_lists_the_nodes_only(self, signed_in):
        _text = signed_in.get("/", headers=HTML).text
        assert 'href="/n/centre"' in _text
        assert 'href="/n/ghost"' in _text
        assert "Sources" not in _text
        assert "item on" in _text

    def test_node_scope_shows_sources_and_datasets(self, signed_in):
        _text = signed_in.get("/n/centre", headers=HTML).text
        assert 'href="/n/centre/query"' in _text
        assert 'href="/n/centre/d/src/alpha"' in _text
        assert 'id="s-src"' in _text

    def test_current_dataset_is_marked(self, signed_in):
        _text = signed_in.get("/n/centre/d/src/alpha", headers=HTML).text
        assert "item leaf on" in _text
        assert '<details class="src" open>' in _text

    def test_query_is_marked(self, signed_in):
        assert 'class="item on" href="/n/centre/query"' in signed_in.get("/n/centre/query", headers=HTML).text

    def test_login_has_no_sidebar(self, web):
        assert "FORTRESS" in web.get("/login").text
        assert 'class="side"' not in web.get("/login").text

    def test_a_node_that_cannot_list_still_renders_the_page(self, signed_in, fake):
        fake.list_sources = lambda: (_ for _ in ()).throw(NodeUnavailableError("lost"))
        assert signed_in.get("/n/centre/query", headers=HTML).status_code == 200


class TestHome:
    def test_lists_every_node_with_its_state(self, signed_in):
        _res = signed_in.get("/", headers=HTML)
        assert _res.status_code == 200
        assert "2 nodes" in _res.text
        assert "centre" in _res.text
        assert "ghost" in _res.text
        assert "unreachable" in _res.text
        assert "1 running" in _res.text

    def test_shows_machine_and_counts(self, signed_in):
        _text = signed_in.get("/", headers=HTML).text
        assert "<polyline" in _text
        assert "cpu" in _text
        assert "4.0 GB / 16.0 GB" in _text

    def test_a_node_that_cannot_list_still_shows(self, signed_in, fake):
        fake.raises = None
        fake.list_sources = lambda: (_ for _ in ()).throw(NodeUnavailableError("node lost"))
        _res = signed_in.get("/", headers=HTML)
        assert _res.status_code == 200
        assert "node lost" in _res.text


class TestNode:
    def test_lists_sources_with_their_datasets(self, signed_in):
        _res = signed_in.get("/n/centre", headers=HTML)
        assert _res.status_code == 200
        assert "src" in _res.text
        assert "/n/centre/d/src/alpha" in _res.text
        assert "Alpha dataset" in _res.text

    def test_extra_source_fields_show_without_a_change(self, signed_in, fake):
        fake.sources = [{"name": "src", "provider": "fake", "vault": "local-vault", "datasets": ["alpha"]}]
        assert "local-vault" in signed_in.get("/n/centre", headers=HTML).text

    def test_unknown_node_is_404(self, signed_in):
        _res = signed_in.get("/n/nope", headers=HTML)
        assert _res.status_code == 404
        assert "not served" in _res.text

    def test_node_down_is_a_502_page(self, signed_in):
        _res = signed_in.get("/n/ghost", headers=HTML)
        assert _res.status_code == 502

    def test_logs_as_json(self, signed_in, fake):
        fake.logs = [{"level": "INFO", "created_at": "2026-01-01T00:00:00+0000", "msg": "hi", "metadata": {}}]
        _res = signed_in.get("/n/centre/s/src/logs", headers=JSON)
        assert _res.status_code == 200
        assert _res.json()[0]["msg"] == "hi"

    def test_logs_of_unknown_source_is_404(self, signed_in):
        assert signed_in.get("/n/centre/s/nope/logs", headers=JSON).status_code == 404

    def test_bad_log_limit_is_400(self, signed_in):
        assert signed_in.get("/n/centre/s/src/logs?limit=x", headers=JSON).status_code == 400


class TestDisplayTimezone:
    @pytest.fixture
    def sydney(self, log, fake, auth):
        from starlette.testclient import TestClient

        from app.service.webhost.service.service import WebHostService

        from .conftest import BASE, make_setting

        _service = WebHostService(
            make_setting(display_timezone="Australia/Sydney"), clients={"centre": fake}, auth=auth
        )
        _service.start()
        with TestClient(_service.asgi_app(), base_url=BASE, follow_redirects=False) as _client:
            assert _client.post("/login", data={"token": auth.token("me")}).status_code == 303
            yield _client
        _service.stop()

    def test_page_times_use_the_setting(self, sydney, fake):
        fake.list_assetfiles = lambda s, d, since=None, until=None: [
            {"name": "a.parquet", "partitions": {"date": "2024-01-01"}, "size": 1, "modified_at": 1_700_000_000.0},
        ]
        assert "2023-11-15 09:13:20 AEDT" in sydney.get("/n/centre/d/src/alpha", headers=HTML).text

    def test_log_times_use_the_setting(self, sydney, fake):
        fake.logs = [{"level": "INFO", "created_at": "2026-01-01T00:00:00+0000", "msg": "hi", "metadata": {}}]
        _res = sydney.get("/n/centre/s/src/logs", headers=JSON)
        assert _res.json()[0]["created_at"] == "2026-01-01 11:00:00 AEDT"

    def test_default_is_utc(self, signed_in, fake):
        fake.logs = [{"level": "INFO", "created_at": "2026-01-01T00:00:00+0000", "msg": "hi", "metadata": {}}]
        _res = signed_in.get("/n/centre/s/src/logs", headers=JSON)
        assert _res.json()[0]["created_at"] == "2026-01-01 00:00:00 UTC"

    def test_bad_timezone_is_rejected(self):
        from pydantic import ValidationError

        from .conftest import make_setting

        with pytest.raises(ValidationError):
            make_setting(display_timezone="Mars/Base")


class TestDataset:
    def test_header_and_partitions_tab(self, signed_in, fake):
        fake.datasets[0]["partitions"] = ["date"]
        _res = signed_in.get("/n/centre/d/src/alpha", headers=HTML)
        assert _res.status_code == 200
        assert "src.alpha" in _res.text
        assert "partitioned by" in _res.text
        assert "no assetfiles yet" in _res.text

    def test_partition_summary_from_assetfiles(self, signed_in, fake):
        fake.list_assetfiles = lambda s, d, since=None, until=None: [
            {"name": "a.parquet", "partitions": {"date": "2024-01-01"}, "size": 2048, "modified_at": 10.0},
            {"name": "b.parquet", "partitions": {"date": "2024-01-02"}, "size": 1024, "modified_at": 20.0},
        ]
        _text = signed_in.get("/n/centre/d/src/alpha", headers=HTML).text
        assert "3.0 KB" in _text
        assert "2024-01-01" in _text and "2024-01-02" in _text
        assert _text.index("b.parquet") < _text.index("a.parquet")

    def test_quality_tab(self, signed_in, fake):
        fake.qualities = _qualities()
        _text = signed_in.get("/n/centre/d/src/alpha?tab=quality", headers=HTML).text
        assert "1 column with nulls" in _text
        assert "2 duplicate rows" in _text
        assert "90.0%" in _text
        assert "no metadata" in _text
        assert "clean" in _text
        assert "<dt>records</dt><dd>3</dd>" in _text

    def test_quality_only_issues(self, signed_in, fake):
        fake.qualities = _qualities()
        _text = signed_in.get("/n/centre/d/src/alpha?tab=quality&only=issues", headers=HTML).text
        assert "d1" in _text
        assert "no metadata" in _text
        assert "d3" not in _text

    def test_quality_all_null_column_is_a_problem(self, signed_in, fake):
        _bad = _qualities()[0]
        _bad["quality"]["columns"][0]["is_all_null"] = True
        fake.qualities = [_bad]
        _text = signed_in.get("/n/centre/d/src/alpha?tab=quality", headers=HTML).text
        assert "1 all-null column" in _text
        assert "q-bad" in _text

    def test_definitions_tab(self, signed_in, fake):
        fake.definitions = [
            {
                "fingerprint": "abcdef0123456789",
                "columns": [{"name": "px", "type": "DOUBLE"}],
                "partitions": [{"date": "d1"}],
            }
        ]
        _text = signed_in.get("/n/centre/d/src/alpha?tab=definitions", headers=HTML).text
        assert "abcdef012345" in _text
        assert "px DOUBLE" in _text

    def test_runs_tab(self, signed_in):
        _text = signed_in.get("/n/centre/d/src/alpha?tab=runs", headers=HTML).text
        assert "run_0" in _text
        assert "completed" in _text
        assert "run dataset" in _text

    def test_started_run_is_polled(self, signed_in, fake):
        fake.runs = [{"id": "run_9", "status": "started", "started_at": 1.0, "duration": 1.0}]
        assert (
            'data-poll="/n/centre/d/src/alpha/runs/run_9"'
            in signed_in.get("/n/centre/d/src/alpha?tab=runs", headers=HTML).text
        )

    def test_unknown_tab_falls_back(self, signed_in):
        assert signed_in.get("/n/centre/d/src/alpha?tab=zzz", headers=HTML).status_code == 200

    def test_unknown_dataset_is_404(self, signed_in):
        assert signed_in.get("/n/centre/d/src/nope", headers=HTML).status_code == 404


class TestRuns:
    def test_submit_runs_the_dataset_and_audits(self, signed_in, fake, log):
        _res = signed_in.post("/n/centre/d/src/alpha/runs", json={"params": {"date": "2024-01-01"}})
        assert _res.status_code == 202
        assert _res.json()["id"] == "run_1"
        assert ("submit_dataset_run", ("src", "alpha", {"date": "2024-01-01"})) in fake.calls
        _meta = log.info.call_args.kwargs["metadata"]
        assert _meta["user"] == "me"
        assert _meta["dataset"] == "src.alpha"

    def test_submit_without_a_body(self, signed_in, fake):
        assert signed_in.post("/n/centre/d/src/alpha/runs").status_code == 202
        assert ("submit_dataset_run", ("src", "alpha", None)) in fake.calls

    def test_submit_with_a_body_that_is_not_json(self, signed_in):
        _res = signed_in.post(
            "/n/centre/d/src/alpha/runs", content=b"{nope", headers={"Content-Type": "application/json"}
        )
        assert _res.status_code == 400

    def test_busy_node_is_503_with_its_message(self, signed_in, fake):
        fake.raises = NodeBusyError("Dataset 'src.alpha' is already running")
        _res = signed_in.post("/n/centre/d/src/alpha/runs")
        assert _res.status_code == 503
        assert _res.json() == {"error": "NodeBusyError", "message": "Dataset 'src.alpha' is already running"}

    def test_poll_a_run(self, signed_in, fake):
        fake.run = {"id": "run_1", "status": "completed", "height": 1, "width": 1}
        _res = signed_in.get("/n/centre/d/src/alpha/runs/run_1", headers=JSON)
        assert _res.status_code == 200
        assert _res.json()["status"] == "completed"
        assert ("get_dataset_run", ("src", "alpha", "run_1")) in fake.calls


class TestQuery:
    def test_page_lists_the_tables(self, signed_in):
        _text = signed_in.get("/n/centre/query", headers=HTML).text
        assert 'data-table="src.alpha"' in _text

    def test_query_returns_the_result(self, signed_in, fake, log):
        _res = signed_in.post("/n/centre/query", json={"sql": "SELECT a FROM src.alpha"})
        assert _res.status_code == 200
        _body = _res.json()
        assert _body["columns"] == ["a"]
        assert _body["rows"] == [[1]]
        assert ("query", ("SELECT a FROM src.alpha",)) in fake.calls
        # The host is one identity on the node, a caller would be refused for a token that cannot delegate
        assert fake.callers == [None]
        assert log.info.call_args.kwargs["metadata"]["user"] == "me"

    @pytest.mark.parametrize("body", [{}, {"sql": ""}, {"sql": "   "}, {"sql": 5}])
    def test_empty_sql_is_400(self, signed_in, body):
        assert signed_in.post("/n/centre/query", json=body).status_code == 400

    def test_too_long_sql_is_400(self, signed_in):
        assert signed_in.post("/n/centre/query", json={"sql": "x" * 100_001}).status_code == 400

    def test_rejected_sql_shows_the_nodes_message(self, signed_in, fake):
        fake.raises = DRARejectedError("only SELECT is allowed")
        _res = signed_in.post("/n/centre/query", json={"sql": "DROP TABLE x"})
        assert _res.status_code == 400
        assert _res.json()["message"] == "only SELECT is allowed"

    def test_unexpected_error_hides_the_detail(self, signed_in, fake, log):
        fake.raises = RuntimeError("secret detail")
        _res = signed_in.post("/n/centre/query", json={"sql": "SELECT 1"})
        assert _res.status_code == 500
        assert "secret detail" not in _res.text
        assert log.error.called
