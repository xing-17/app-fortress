from __future__ import annotations

import polars as pl

from app.service.mcphost.service.tools import build_server

from .conftest import write_assetfile
from .test_tools_unit import call, data, text


class TestThroughANode:
    """The tools over a real node, once through `LocalNodeClient` and once over HTTP."""

    def _server(self, node_client, log):
        return build_server(node_client, log)

    def test_list_datasets(self, node_client, log):
        _res = data(call(self._server(node_client, log), "list_datasets"))
        assert sorted(d["dataset"] for d in _res) == ["src.alpha", "src.beta"]

    def test_schema_then_query(self, node_client, log, source):
        write_assetfile(source, "beta", "a.parquet", pl.DataFrame({"v": [1, 2]}), {"year": "2023"})
        write_assetfile(source, "beta", "b.parquet", pl.DataFrame({"v": [10, 20]}), {"year": "2024"})
        _server = self._server(node_client, log)

        _schema = data(call(_server, "get_schema", {"dataset": "src.beta"}))
        assert _schema["partition_keys"] == ["year"]
        assert _schema["definitions"][0]["columns"] == [{"name": "v", "type": "Int64"}]
        assert _schema["definitions"][0]["partition_range"] == {"year": ["2023", "2024"]}

        _res = data(call(_server, "query", {"sql": "SELECT sum(v) AS total FROM src.beta WHERE year = '2024'"}))
        assert _res["rows"] == [[30]]

    def test_quality(self, node_client, log, source):
        write_assetfile(source, "alpha", "a.parquet", pl.DataFrame({"v": [1, None, 3]}))
        _res = data(call(self._server(node_client, log), "get_quality", {"dataset": "src.alpha"}))
        _file = _res["files"][0]
        assert _file["rows"] == 3
        assert "v" in _file["null_rates"]

    def test_a_rejected_statement_reaches_the_ai_as_a_tool_error(self, node_client, log):
        _res = call(self._server(node_client, log), "query", {"sql": "DROP TABLE x"})
        assert _res.is_error

    def test_an_unknown_dataset_reaches_the_ai_as_a_tool_error(self, node_client, log):
        _res = call(self._server(node_client, log), "get_schema", {"dataset": "src.nope"})
        assert _res.is_error
        assert "not found" in text(_res)
