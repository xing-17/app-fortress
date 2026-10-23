from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from mcp import Client

from app.service.mcphost.service.tools import build_server
from app.service.node.dra import (
    DRABusyError,
    DRADataResult,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
    NodeUnknownError,
)

from .fakes import FakeNodeClient


def call(server, tool: str, arguments: dict[str, Any] | None = None):
    async def _run():
        async with Client(server) as _client:
            return await _client.call_tool(tool, arguments or {})

    return asyncio.run(_run())


def tools_of(server):
    async def _run():
        async with Client(server) as _client:
            return (await _client.list_tools()).tools

    return asyncio.run(_run())


def data(result):
    _res = result.structured_content
    if _res is None:
        _res = json.loads(result.content[0].text)
    if isinstance(_res, dict) and set(_res) == {"result"}:
        return _res["result"]
    return _res


def text(result) -> str:
    return result.content[0].text


def _file(name, partitions, modified_at, quality):
    return {
        "assetfile": {"name": name, "partitions": partitions, "modified_at": modified_at},
        "quality": quality,
    }


def _quality(columns, height=10, complete_rows=10, duplicate_rows=0):
    return {
        "height": height,
        "complete_rows": complete_rows,
        "duplicate_rows": duplicate_rows,
        "columns": columns,
    }


def _column(name, null_rate=0.0, is_constant=False, is_all_null=False):
    return {"name": name, "null_rate": null_rate, "is_constant": is_constant, "is_all_null": is_all_null}


@pytest.fixture
def fake():
    return FakeNodeClient()


@pytest.fixture
def server(fake, log):
    return build_server({"centre": fake}, log)


def _info(source, name):
    return {
        "source": source,
        "dataset": f"{source}.{name}",
        "name": name,
        "description": f"{name} dataset",
        "frequency": "daily",
        "partitions": ["date"],
    }


class TestToolList:
    def test_exposes_the_tools(self, server):
        assert {t.name for t in tools_of(server)} == {
            "list_nodes",
            "list_datasets",
            "get_schema",
            "get_quality",
            "query",
        }

    def test_every_tool_is_described(self, server):
        for _tool in tools_of(server):
            assert len(_tool.description) > 50, _tool.name

    def test_query_description_warns_about_the_limits(self, server):
        _query = next(t for t in tools_of(server) if t.name == "query")
        assert "NOT saved" in _query.description
        assert "truncated" in _query.description
        assert "VARCHAR" in _query.description

    def test_name_and_instructions(self, fake, log):
        _server = build_server({"centre": fake}, log, name="snt")
        assert _server.name == "snt"
        assert "<source>.<dataset>" in _server.instructions

    def test_needs_a_node(self, log):
        with pytest.raises(ValueError, match="at least one node"):
            build_server({}, log)


class TestListNodes:
    def test_lists_the_node_with_its_sources(self, server, fake):
        fake.sources = [{"name": "src"}, {"name": "other"}]
        assert data(call(server, "list_nodes")) == [{"name": "centre", "reachable": True, "sources": ["src", "other"]}]

    def test_a_node_that_is_down_is_marked_not_reachable(self, server, fake):
        fake.raises = NodeUnavailableError("node http://secret-host:8800 is unreachable")
        _res = call(server, "list_nodes")
        assert not _res.is_error
        _node = data(_res)[0]
        assert _node["reachable"] is False
        assert "unreachable or too slow" in _node["error"]
        assert "sources" not in _node
        assert "secret-host" not in text(_res)


class TestListDatasets:
    def test_maps_the_fields_the_ai_needs(self, server):
        _res = data(call(server, "list_datasets"))
        assert _res == {
            "datasets": [
                {
                    "node": "centre",
                    "dataset": "src.alpha",
                    "description": "Alpha dataset",
                    "frequency": "daily",
                    "partition_keys": ["date"],
                }
            ],
            "nodes": [{"name": "centre", "reachable": True}],
        }

    def test_passes_the_source(self, server, fake):
        call(server, "list_datasets", {"source": "src"})
        assert ("list_datasets", ("src",)) in fake.calls

    def test_unknown_source_is_an_error(self, server):
        _res = call(server, "list_datasets", {"source": "nope"})
        assert _res.is_error
        assert "Source 'nope' not found" in text(_res)

    def test_a_node_that_is_down_is_marked_not_reachable(self, server, fake):
        fake.raises = NodeUnavailableError("node http://secret-host:8800 is unreachable")
        _res = call(server, "list_datasets")
        assert not _res.is_error
        _body = data(_res)
        assert _body["datasets"] == []
        assert _body["nodes"][0]["reachable"] is False
        assert "secret-host" not in text(_res)


class TestMultipleNodes:
    @pytest.fixture
    def snt(self):
        _node = FakeNodeClient()
        _node.datasets = [_info("tushare", "tradedates")]
        _node.sources = [{"name": "tushare"}]
        return _node

    @pytest.fixture
    def sh(self):
        _node = FakeNodeClient()
        _node.datasets = [_info("nswvg", "psi")]
        _node.sources = [{"name": "nswvg"}]
        return _node

    @pytest.fixture
    def server(self, snt, sh, log):
        return build_server({"snt": snt, "sh": sh}, log)

    def test_list_nodes_lists_them_all(self, server, sh):
        sh.raises = NodeUnavailableError("gone")
        _res = data(call(server, "list_nodes"))
        assert [(n["name"], n["reachable"]) for n in _res] == [("snt", True), ("sh", False)]
        assert _res[0]["sources"] == ["tushare"]

    def test_list_datasets_merges_the_nodes(self, server):
        _res = data(call(server, "list_datasets"))
        assert [(d["node"], d["dataset"]) for d in _res["datasets"]] == [
            ("snt", "tushare.tradedates"),
            ("sh", "nswvg.psi"),
        ]
        assert all(n["reachable"] for n in _res["nodes"])

    def test_list_datasets_keeps_the_others_when_a_node_is_down(self, server, sh):
        sh.raises = NodeUnavailableError("gone")
        _res = data(call(server, "list_datasets"))
        assert [d["dataset"] for d in _res["datasets"]] == ["tushare.tradedates"]
        assert [(n["name"], n["reachable"]) for n in _res["nodes"]] == [("snt", True), ("sh", False)]

    def test_list_datasets_of_a_source_held_by_one_node(self, server):
        _res = data(call(server, "list_datasets", {"source": "nswvg"}))
        assert [d["node"] for d in _res["datasets"]] == ["sh"]
        assert all(n["reachable"] for n in _res["nodes"])

    def test_list_datasets_of_one_node(self, server, snt):
        _res = data(call(server, "list_datasets", {"node": "sh"}))
        assert [n["name"] for n in _res["nodes"]] == ["sh"]
        assert [c[0] for c in snt.calls] == []

    def test_list_datasets_of_a_source_no_node_has(self, server):
        _res = call(server, "list_datasets", {"source": "nope"})
        assert _res.is_error
        assert "not found on any node" in text(_res)

    def test_schema_is_routed_to_the_node_that_holds_the_dataset(self, server, snt, sh):
        _res = data(call(server, "get_schema", {"dataset": "nswvg.psi"}))
        assert _res["node"] == "sh"
        assert ("list_definitions", ("nswvg", "psi")) in sh.calls
        assert "list_definitions" not in [c[0] for c in snt.calls]

    def test_quality_is_routed_to_the_node_that_holds_the_dataset(self, server, snt, sh):
        _res = data(call(server, "get_quality", {"dataset": "tushare.tradedates"}))
        assert _res["node"] == "snt"
        assert "list_qualities" not in [c[0] for c in sh.calls]

    def test_a_dataset_on_several_nodes_needs_the_node(self, server, snt, sh):
        sh.datasets.append(_info("tushare", "tradedates"))
        _res = call(server, "get_schema", {"dataset": "tushare.tradedates"})
        assert _res.is_error
        assert "pass `node`" in text(_res)
        assert data(call(server, "get_schema", {"dataset": "tushare.tradedates", "node": "sh"}))["node"] == "sh"

    def test_an_unknown_dataset_is_not_found(self, server):
        _res = call(server, "get_schema", {"dataset": "src.nope"})
        assert _res.is_error
        assert "not found on any node" in text(_res)

    def test_a_dataset_that_may_be_on_a_node_that_is_down(self, server, sh):
        sh.raises = NodeUnavailableError("gone")
        _res = call(server, "get_schema", {"dataset": "nswvg.psi"})
        assert _res.is_error
        assert "['sh']" in text(_res)

    def test_query_needs_the_node(self, server, snt, sh):
        _res = call(server, "query", {"sql": "SELECT 1"})
        assert _res.is_error
        assert "pass `node`" in text(_res)
        assert "query" not in [c[0] for c in snt.calls + sh.calls]

    def test_query_runs_on_the_node_asked_for(self, server, snt, sh):
        _res = data(call(server, "query", {"sql": "SELECT 1", "node": "sh"}))
        assert _res["node"] == "sh"
        assert [c[0] for c in sh.calls] == ["query"]
        assert snt.calls == []

    def test_unknown_node_is_an_error(self, server):
        _res = call(server, "query", {"sql": "SELECT 1", "node": "nope"})
        assert _res.is_error
        assert "unknown node" in text(_res)


class TestGetSchema:
    def _definitions(self):
        return [
            {
                "fingerprint": "old",
                "columns": [{"name": "a", "type": "BIGINT"}],
                "partitions": [{"date": "2024-01-01"}],
            },
            {
                "fingerprint": "new",
                "columns": [{"name": "a", "type": "BIGINT"}, {"name": "b", "type": "VARCHAR"}],
                "partitions": [{"date": "2024-02-01"}, {"date": "2024-03-01"}, {"date": "2024-02-15"}],
            },
        ]

    def test_returns_the_columns_and_partition_ranges(self, server, fake):
        fake.definitions = self._definitions()
        _res = data(call(server, "get_schema", {"dataset": "src.alpha"}))
        assert _res["dataset"] == "src.alpha"
        assert _res["description"] == "Alpha dataset"
        assert _res["partition_keys"] == ["date"]
        _new = _res["definitions"][0]
        assert _new["columns"] == [{"name": "a", "type": "BIGINT"}, {"name": "b", "type": "VARCHAR"}]
        assert _new["partition_count"] == 3
        assert _new["partition_range"] == {"date": ["2024-02-01", "2024-03-01"]}

    def test_the_most_common_definition_comes_first(self, server, fake):
        fake.definitions = self._definitions()
        _res = data(call(server, "get_schema", {"dataset": "src.alpha"}))
        assert [d["partition_count"] for d in _res["definitions"]] == [3, 1]

    def test_dataset_without_definitions(self, server, fake):
        _res = data(call(server, "get_schema", {"dataset": "src.alpha"}))
        assert _res["definitions"] == []

    def test_splits_the_dataset_name(self, server, fake):
        call(server, "get_schema", {"dataset": "src.alpha"})
        assert ("list_definitions", ("src", "alpha")) in fake.calls

    @pytest.mark.parametrize("name", ["alpha", "", ".alpha", "src.", "a.b.c", "  "])
    def test_malformed_dataset_name_tells_the_expected_form(self, server, fake, name):
        _res = call(server, "get_schema", {"dataset": name})
        assert _res.is_error
        assert "<source>.<dataset>" in text(_res)
        assert fake.calls == []

    def test_unknown_dataset_keeps_the_node_message(self, server, fake):
        fake.raises = NodeDatasetNotFoundError("Dataset 'src.nope' not found on this node")
        _res = call(server, "get_schema", {"dataset": "src.nope"})
        assert _res.is_error
        assert "Dataset 'src.nope' not found on this node" in text(_res)


class TestGetQuality:
    def test_summarizes_a_file(self, server, fake):
        _q = _quality(
            [
                _column("a"),
                _column("b", null_rate=0.25),
                _column("c", is_constant=True),
                _column("d", null_rate=1.0, is_constant=True, is_all_null=True),
            ],
            height=8,
            complete_rows=6,
            duplicate_rows=1,
        )
        fake.qualities = [_file("a.parquet", {"date": "2024-01-01"}, 10.0, _q)]
        _res = data(call(server, "get_quality", {"dataset": "src.alpha"}))
        assert _res["dataset"] == "src.alpha"
        assert _res["total_files"] == 1
        assert _res["files"] == [
            {
                "partitions": {"date": "2024-01-01"},
                "name": "a.parquet",
                "checked": True,
                "rows": 8,
                "complete_rows": 6,
                "duplicate_rows": 1,
                "null_rates": {"b": 0.25, "d": 1.0},
                "constant_columns": ["c"],
                "all_null_columns": ["d"],
            }
        ]

    def test_file_without_a_quality_record(self, server, fake):
        fake.qualities = [_file("a.parquet", {}, 10.0, None)]
        _res = data(call(server, "get_quality", {"dataset": "src.alpha"}))
        assert _res["files"] == [{"partitions": {}, "name": "a.parquet", "checked": False}]

    def test_latest_files_come_first_and_the_limit_applies(self, server, fake):
        fake.qualities = [_file(f"{i}.parquet", {}, float(i), _quality([])) for i in range(5)]
        _res = data(call(server, "get_quality", {"dataset": "src.alpha", "limit": 2}))
        assert _res["total_files"] == 5
        assert [f["name"] for f in _res["files"]] == ["4.parquet", "3.parquet"]

    def test_limit_is_clamped(self, server, fake):
        fake.qualities = [_file(f"{i}.parquet", {}, float(i), _quality([])) for i in range(3)]
        assert len(data(call(server, "get_quality", {"dataset": "src.alpha", "limit": 0}))["files"]) == 1
        assert len(data(call(server, "get_quality", {"dataset": "src.alpha", "limit": -5}))["files"]) == 1
        assert len(data(call(server, "get_quality", {"dataset": "src.alpha", "limit": 10_000}))["files"]) == 3

    def test_default_limit(self, server, fake):
        fake.qualities = [_file(f"{i}.parquet", {}, float(i), _quality([])) for i in range(30)]
        assert len(data(call(server, "get_quality", {"dataset": "src.alpha"}))["files"]) == 20

    def test_malformed_dataset_name(self, server):
        _res = call(server, "get_quality", {"dataset": "alpha"})
        assert _res.is_error
        assert "<source>.<dataset>" in text(_res)


class TestQuery:
    def test_returns_the_result(self, server, fake):
        fake.result = DRADataResult(columns=["n", "s"], types=["BIGINT", "VARCHAR"], rows=[[1, "a"], [2, "b"]])
        _res = data(call(server, "query", {"sql": "SELECT n, s FROM src.alpha"}))
        assert _res["columns"] == ["n", "s"]
        assert _res["types"] == ["BIGINT", "VARCHAR"]
        assert _res["rows"] == [[1, "a"], [2, "b"]]
        assert _res["truncated"] is False
        assert ("query", ("SELECT n, s FROM src.alpha",)) in fake.calls

    def test_tells_when_the_result_is_truncated(self, server, fake):
        fake.result = DRADataResult(columns=["a"], types=["BIGINT"], rows=[[1]], truncated=True, truncated_by="rows")
        _res = data(call(server, "query", {"sql": "SELECT a FROM src.alpha"}))
        assert _res["truncated"] is True
        assert _res["truncated_by"] == "rows"

    def test_missing_sql_is_an_error(self, server):
        assert call(server, "query", {}).is_error

    @pytest.mark.parametrize(
        "error",
        [
            DRARejectedError("only a single SELECT statement is allowed"),
            DRAQueryError("BinderException: column nope not found"),
            DRAQueryTimeoutError("query exceeded 30.0s"),
            DRABusyError("every session is busy, retry later"),
            NodeBadRequestError("body must be JSON"),
        ],
    )
    def test_errors_for_the_caller_keep_their_message(self, server, fake, error):
        fake.raises = error
        _res = call(server, "query", {"sql": "SELECT 1"})
        assert _res.is_error
        assert str(error) in text(_res)


class TestNodeFailures:
    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (
                NodeUnauthorizedError("node http://secret-host:8800 rejected the token"),
                "rejected the token of this host",
            ),
            (NodeUnavailableError("node http://secret-host:8800 is unreachable"), "unreachable or too slow"),
            (NodeUnknownError("node http://secret-host:8800 answered 500"), "Unexpected error"),
            (RuntimeError("boom at /internal/path"), "Unexpected error"),
        ],
    )
    def test_the_ai_gets_a_fixed_message_and_no_detail(self, server, fake, error, expected):
        fake.raises = error
        _res = call(server, "query", {"sql": "SELECT 1"})
        assert _res.is_error
        assert expected in text(_res)
        assert "secret-host" not in text(_res)
        assert "boom" not in text(_res)


class TestCallTrace:
    def test_a_good_call_is_logged_with_rows_and_elapsed_time(self, server, fake, log):
        fake.result = DRADataResult(columns=["a"], types=["BIGINT"], rows=[[1], [2]])
        call(server, "query", {"sql": "SELECT a FROM src.alpha"})
        _args = log.info.call_args
        assert _args.args[0] == "tool ok: query"
        assert _args.kwargs["metadata"]["tool"] == "query"
        assert _args.kwargs["metadata"]["arguments"] == {"sql": "SELECT a FROM src.alpha"}
        assert _args.kwargs["metrics"]["rows"] == 2
        assert _args.kwargs["metrics"]["truncated"] == 0.0
        assert _args.kwargs["metrics"]["elapsed_ms"] >= 0

    def test_truncation_is_logged(self, server, fake, log):
        fake.result = DRADataResult(columns=["a"], types=["BIGINT"], rows=[[1]], truncated=True, truncated_by="size")
        call(server, "query", {"sql": "SELECT a FROM src.alpha"})
        assert log.info.call_args.kwargs["metrics"]["truncated"] == 1.0

    def test_a_failed_call_is_logged_with_the_error_type(self, server, fake, log):
        fake.raises = DRARejectedError("no")
        call(server, "query", {"sql": "DROP TABLE x"})
        _args = log.warning.call_args
        assert _args.args[0] == "tool failed: query"
        assert _args.kwargs["metadata"]["error"] == "DRARejectedError"
        assert _args.kwargs["metrics"]["elapsed_ms"] >= 0

    def test_failure_log_has_the_error_type_not_the_detail(self, server, fake, log):
        fake.raises = NodeUnavailableError("node http://secret-host:8800 is unreachable")
        call(server, "query", {"sql": "SELECT 1"})
        _meta = log.warning.call_args.kwargs["metadata"]
        assert _meta["error"] == "NodeUnavailableError"
        assert "secret-host" not in str(_meta)

    def test_long_sql_is_clipped_in_the_log(self, server, log):
        call(server, "query", {"sql": "SELECT '" + "x" * 2000 + "'"})
        assert len(log.info.call_args.kwargs["metadata"]["arguments"]["sql"]) == 500

    def test_every_tool_is_traced(self, server, fake, log):
        call(server, "list_datasets")
        call(server, "get_schema", {"dataset": "src.alpha"})
        call(server, "get_quality", {"dataset": "src.alpha"})
        call(server, "query", {"sql": "SELECT 1"})
        _logged = [c.args[0] for c in log.info.call_args_list]
        assert _logged == [
            "tool start: list_datasets",
            "tool ok: list_datasets",
            "tool start: get_schema",
            "tool ok: get_schema",
            "tool start: get_quality",
            "tool ok: get_quality",
            "tool start: query",
            "tool ok: query",
        ]
