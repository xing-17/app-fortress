from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
import requests

from app.resource._client.web.client import WebClient
from app.resource._client.web.errors import WebChallengeError


def _response(
    status: int = 200,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> requests.Response:
    _resp = requests.Response()
    _resp.status_code = status
    _resp.url = "https://example.com/file"
    _resp.raw = io.BytesIO(body)
    _resp.headers.update(headers or {})
    return _resp


class _FakeSession:
    def __init__(self, response: requests.Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> requests.Response:
        self.calls.append(kwargs)
        return self.response

    def close(self) -> None:
        pass


def _client(response: requests.Response) -> tuple[WebClient, _FakeSession]:
    _web = WebClient()
    _session = _FakeSession(response)
    _web._session = _session  # type: ignore[assignment]
    return _web, _session


class TestSession:
    def test_session_is_created_once(self):
        _web = WebClient()
        assert _web.session is _web.session
        _web.close()

    def test_close_discards_session(self):
        _web = WebClient()
        _first = _web.session
        _web.close()
        assert _web.session is not _first
        _web.close()

    def test_close_without_session_is_noop(self):
        WebClient().close()


class TestRequest:
    def test_forwards_arguments_to_session(self):
        _web, _session = _client(_response())
        _web.request(
            "GET",
            "https://example.com",
            params={"a": "1"},
            headers={"X-Test": "1"},
            stream=True,
            timeout=5,
        )
        assert _session.calls == [
            {
                "method": "GET",
                "url": "https://example.com",
                "params": {"a": "1"},
                "headers": {"X-Test": "1"},
                "stream": True,
                "timeout": 5,
            }
        ]

    def test_returns_response_on_success(self):
        _resp = _response(body=b"ok")
        _web, _ = _client(_resp)
        assert _web.request("GET", "https://example.com") is _resp

    def test_http_error_is_raised(self):
        _web, _ = _client(_response(status=404))
        with pytest.raises(requests.HTTPError):
            _web.request("GET", "https://example.com")

    def test_challenge_raises_dedicated_error(self):
        _resp = _response(status=403, headers={"cf-mitigated": "challenge"})
        _web, _ = _client(_resp)
        with pytest.raises(WebChallengeError) as _info:
            _web.request("GET", "https://example.com")
        assert _info.value.response is _resp

    def test_challenge_header_is_case_insensitive(self):
        _resp = _response(status=403, headers={"cf-mitigated": "Challenge"})
        _web, _ = _client(_resp)
        with pytest.raises(WebChallengeError):
            _web.request("GET", "https://example.com")

    def test_challenge_error_is_an_http_error(self):
        assert issubclass(WebChallengeError, requests.HTTPError)

    def test_plain_403_is_not_a_challenge(self):
        _web, _ = _client(_response(status=403))
        with pytest.raises(requests.HTTPError) as _info:
            _web.request("GET", "https://example.com")
        assert not isinstance(_info.value, WebChallengeError)


class TestDownload:
    def test_writes_content_to_path(self, tmp_path: Path):
        _web, _ = _client(_response(body=b"hello"))
        _target = tmp_path / "a.zip"
        assert _web.download("https://example.com/a.zip", _target) == _target
        assert _target.read_bytes() == b"hello"

    def test_creates_missing_parent_directories(self, tmp_path: Path):
        _web, _ = _client(_response(body=b"x"))
        _target = tmp_path / "nested" / "deeper" / "a.zip"
        _web.download("https://example.com/a.zip", _target)
        assert _target.exists()

    def test_streams_in_chunks(self, tmp_path: Path):
        _web, _session = _client(_response(body=b"abcdefghij"))
        _target = tmp_path / "a.bin"
        _web.download("https://example.com/a.bin", _target, chunk_size=3)
        assert _target.read_bytes() == b"abcdefghij"
        assert _session.calls[0]["stream"] is True

    def test_leaves_no_part_file_on_success(self, tmp_path: Path):
        _web, _ = _client(_response(body=b"x"))
        _web.download("https://example.com/a.zip", tmp_path / "a.zip")
        assert [_p.name for _p in tmp_path.iterdir()] == ["a.zip"]

    def test_overwrites_existing_file(self, tmp_path: Path):
        _target = tmp_path / "a.zip"
        _target.write_bytes(b"old")
        _web, _ = _client(_response(body=b"new"))
        _web.download("https://example.com/a.zip", _target)
        assert _target.read_bytes() == b"new"

    def test_failed_request_writes_nothing(self, tmp_path: Path):
        _web, _ = _client(_response(status=500))
        _target = tmp_path / "a.zip"
        with pytest.raises(requests.HTTPError):
            _web.download("https://example.com/a.zip", _target)
        assert list(tmp_path.iterdir()) == []

    def test_challenge_writes_nothing(self, tmp_path: Path):
        _resp = _response(status=403, headers={"cf-mitigated": "challenge"})
        _web, _ = _client(_resp)
        with pytest.raises(WebChallengeError):
            _web.download("https://example.com/a.zip", tmp_path / "a.zip")
        assert list(tmp_path.iterdir()) == []
