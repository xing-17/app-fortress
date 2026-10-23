from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import SecretStr

from app.service.node.client.httpnode import HttpNodeClient
from app.service.node.dra import (
    DRABusyError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
    NodeUnknownError,
)
from app.setting.service import NodeEndpointSetting

_TOKEN = "t0ken-secret-value"


def _client(handler, endpoint="http://node") -> HttpNodeClient:
    _http = httpx.Client(transport=httpx.MockTransport(handler), base_url=endpoint)
    return HttpNodeClient(endpoint=endpoint, token=_TOKEN, client=_http)


def _json(status, body):
    return lambda request: httpx.Response(status, json=body)


class TestConstruction:
    @pytest.mark.parametrize("token", ["", "   ", "\n"])
    def test_empty_token_raises(self, token):
        with pytest.raises(ValueError, match="token"):
            HttpNodeClient(endpoint="http://node", token=token)

    def test_accepts_a_secret_str(self):
        _client_ = HttpNodeClient(endpoint="http://node", token=SecretStr(_TOKEN))
        _client_.close()

    def test_from_setting(self):
        _setting = NodeEndpointSetting(name="snt", endpoint="http://node:8800/", token=_TOKEN)
        _client_ = HttpNodeClient.from_setting(_setting)
        assert repr(_client_) == "HttpNodeClient(endpoint='http://node:8800')"
        _client_.close()

    def test_from_setting_without_token_raises(self):
        _setting = NodeEndpointSetting(name="snt", endpoint="http://node")
        with pytest.raises(ValueError, match="snt"):
            HttpNodeClient.from_setting(_setting)

    def test_repr_hides_the_token(self):
        _client_ = HttpNodeClient(endpoint="http://node", token=_TOKEN)
        assert _TOKEN not in repr(_client_)
        _client_.close()

    def test_close_keeps_an_injected_client_open(self):
        _http = httpx.Client(transport=httpx.MockTransport(_json(200, [])), base_url="http://node")
        HttpNodeClient(endpoint="http://node", token=_TOKEN, client=_http).close()
        assert not _http.is_closed
        _http.close()

    def test_close_closes_its_own_client(self):
        _client_ = HttpNodeClient(endpoint="http://node", token=_TOKEN)
        _client_.close()
        assert _client_._client.is_closed


class TestRequest:
    def test_sends_the_bearer_token(self):
        _seen = []

        def _handler(request):
            _seen.append(request.headers["authorization"])
            return httpx.Response(200, json=[])

        _client(_handler).list_sources()
        assert _seen == [f"Bearer {_TOKEN}"]

    def test_names_are_one_path_segment(self):
        _seen = []

        def _handler(request):
            _seen.append(request.url.raw_path.decode())
            return httpx.Response(200, json={})

        _client(_handler).get_dataset("a/b", "c d")
        assert _seen == ["/internal/datasets/a%2Fb/c%20d"]

    def test_window_goes_as_query_params(self):
        _seen = []

        def _handler(request):
            _seen.append(dict(request.url.params))
            return httpx.Response(200, json=[])

        from datetime import datetime

        _since = datetime(2026, 10, 22, 8, 30, tzinfo=timezone.utc)
        _client(_handler).list_assetfiles("s", "d", since=_since, until=1700000000.5)
        assert _seen == [{"since": "2026-10-22T08:30:00+00:00", "until": "1700000000.5"}]

    def test_window_datetimes_are_sent_as_utc(self):
        _seen = []

        def _handler(request):
            _seen.append(dict(request.url.params))
            return httpx.Response(200, json=[])

        _naive = datetime(2026, 10, 22, 8, 30)
        _shanghai = datetime(2026, 10, 22, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        _client(_handler).list_assetfiles("s", "d", since=_naive, until=_shanghai)
        assert _seen == [{"since": "2026-10-22T08:30:00+00:00", "until": "2026-10-22T08:30:00+00:00"}]

    def test_no_window_sends_no_params(self):
        _seen = []

        def _handler(request):
            _seen.append(dict(request.url.params))
            return httpx.Response(200, json=[])

        _client(_handler).list_assetfiles("s", "d")
        assert _seen == [{}]

    def test_list_datasets_sends_the_source(self):
        _seen = []

        def _handler(request):
            _seen.append(dict(request.url.params))
            return httpx.Response(200, json=[])

        _client(_handler).list_datasets("src")
        assert _seen == [{"source": "src"}]

    def test_query_posts_the_sql(self):
        _seen = []

        def _handler(request):
            _seen.append(json.loads(request.content))
            return httpx.Response(200, json={"columns": ["a"], "types": ["INTEGER"], "rows": [[1]]})

        _res = _client(_handler).query("SELECT 1 AS a")
        assert _seen == [{"sql": "SELECT 1 AS a"}]
        assert _res.rows == [[1]]

    def test_query_names_the_caller_in_a_header(self):
        _seen = []

        def _handler(request):
            _seen.append((request.headers.get("x-fortress-caller"), request.headers["authorization"]))
            return httpx.Response(200, json={"columns": ["a"], "types": ["INTEGER"], "rows": [[1]]})

        _client(_handler).query("SELECT 1 AS a", caller="phone")
        assert _seen == [("phone", f"Bearer {_TOKEN}")]

    def test_query_without_a_caller_sends_no_header(self):
        _seen = []

        def _handler(request):
            _seen.append("x-fortress-caller" in request.headers)
            return httpx.Response(200, json={"columns": ["a"], "types": ["INTEGER"], "rows": [[1]]})

        _client(_handler).query("SELECT 1 AS a")
        assert _seen == [False]


class TestErrors:
    @pytest.mark.parametrize(
        ("status", "name", "expected"),
        [
            (404, "NodeSourceNotFoundError", NodeSourceNotFoundError),
            (404, "NodeDatasetNotFoundError", NodeDatasetNotFoundError),
            (400, "NodeBadRequestError", NodeBadRequestError),
            (400, "DRARejectedError", DRARejectedError),
            (400, "DRAQueryError", DRAQueryError),
            (408, "DRAQueryTimeoutError", DRAQueryTimeoutError),
            (503, "DRABusyError", DRABusyError),
        ],
    )
    def test_named_errors_keep_their_type_and_message(self, status, name, expected):
        _body = {"error": name, "message": "what to fix"}
        with pytest.raises(expected, match="what to fix"):
            _client(_json(status, _body)).query("SELECT 1")

    def test_unauthorized(self):
        with pytest.raises(NodeUnauthorizedError) as _info:
            _client(_json(401, {"error": "unauthorized"})).list_sources()
        assert _TOKEN not in str(_info.value)

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (400, NodeBadRequestError),
            (413, NodeBadRequestError),
            (408, DRAQueryTimeoutError),
            (503, DRABusyError),
            (500, NodeUnknownError),
            (502, NodeUnknownError),
        ],
    )
    def test_unnamed_errors_are_mapped_by_status(self, status, expected):
        with pytest.raises(expected):
            _client(_json(status, {"error": "something"})).list_sources()

    def test_internal_error_does_not_leak_the_body(self):
        with pytest.raises(NodeUnknownError) as _info:
            _client(_json(500, {"error": "internal error", "message": "secret stack detail"})).list_sources()
        assert "secret stack detail" not in str(_info.value)

    def test_unknown_route_is_unknown_error(self):
        _handler = lambda request: httpx.Response(404, text="Not Found")  # noqa: E731
        with pytest.raises(NodeUnknownError):
            _client(_handler).list_sources()

    def test_non_json_success_raises(self):
        _handler = lambda request: httpx.Response(200, text="<html>")  # noqa: E731
        with pytest.raises(NodeUnknownError, match="not JSON"):
            _client(_handler).list_sources()

    def test_unreachable_node(self):
        def _handler(request):
            raise httpx.ConnectError("refused")

        with pytest.raises(NodeUnavailableError, match="unreachable"):
            _client(_handler).list_sources()

    def test_timeout(self):
        def _handler(request):
            raise httpx.ReadTimeout("slow")

        with pytest.raises(NodeUnavailableError, match="in time"):
            _client(_handler).query("SELECT 1")

    def test_unavailable_error_does_not_leak_the_token(self):
        def _handler(request):
            raise httpx.ConnectError("refused")

        with pytest.raises(NodeUnavailableError) as _info:
            _client(_handler).list_sources()
        assert _TOKEN not in str(_info.value)


class TestHealth:
    def test_healthy(self):
        assert _client(_json(200, {"state": "running"})).health() == {"state": "running"}

    def test_503_still_returns_the_state(self):
        _res = _client(_json(503, {"state": "stopped"})).health()
        assert _res == {"state": "stopped"}

    def test_other_status_raises(self):
        with pytest.raises(NodeUnknownError):
            _client(_json(500, {"error": "internal error"})).health()

    def test_non_json_raises(self):
        _handler = lambda request: httpx.Response(200, text="ok")  # noqa: E731
        with pytest.raises(NodeUnknownError):
            _client(_handler).health()


class TestAgainstTheNode:
    def test_a_wrong_token_is_unauthorized(self, app_client):
        _client_ = HttpNodeClient(endpoint="http://testserver", token="wrong", client=app_client)
        with pytest.raises(NodeUnauthorizedError):
            _client_.list_sources()

    def test_health_needs_no_token(self, app_client):
        _client_ = HttpNodeClient(endpoint="http://testserver", token="wrong", client=app_client)
        assert _client_.health()["is_running"] is True

    def test_node_internal_error_is_unknown(self, service, app_client, auth, monkeypatch):
        def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(service, "list_sources", _boom)
        _client_ = HttpNodeClient(endpoint="http://testserver", token=auth.token("alice"), client=app_client)
        with pytest.raises(NodeUnknownError):
            _client_.list_sources()
