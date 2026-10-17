from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import requests

from .errors import (
    WebChallengeError,
)


class WebClient:
    """
    HTTP client with a pooled session

    Attributes:
    ----------
        session (requests.Session):
            Lazily created and cached session, shared by all requests of this client

    Methods:
    -------
        close():
            Close the HTTP session.
        request(method, url, params, headers, stream, timeout):
            Send an HTTP request.
        download(url, path, params, headers, timeout, chunk_size):
            Download a file from the specified URL to the given path.

    """

    def __init__(self) -> None:
        # Initialize the HTTP session and session lock
        self._session: requests.Session | None = None
        self._session_lock: threading.RLock = threading.RLock()

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    _session = requests.Session()
                    self._session = _session
        return self._session

    def close(self) -> None:
        with self._session_lock:
            if self._session is not None:
                self._session.close()
                self._session = None

    def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ) -> requests.Response:
        _response: requests.Response = self.session.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            stream=stream,
            timeout=timeout,
        )
        _resp_headers = _response.headers

        # Check for Cloudflare challenge before raising for status
        _mitigated: str = _resp_headers.get("cf-mitigated", "").lower()
        if _mitigated == "challenge":
            _response.close()
            raise WebChallengeError("Request blocked by challenge", response=_response)

        # Raise an HTTPError if the response contains an unsuccessful status code
        try:
            _response.raise_for_status()
        except requests.HTTPError:
            _response.close()
            raise
        return _response

    def download(
        self,
        url: str,
        path: Path,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        _path: Path = Path(path)
        _part: Path = _path.with_name(_path.name + ".part")
        _path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _response: requests.Response = self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            stream=True,
            timeout=timeout,
        )
        try:
            with _part.open("wb") as _file:
                for _chunk in _response.iter_content(chunk_size=chunk_size):
                    _file.write(_chunk)
        finally:
            _response.close()
        os.replace(_part, _path)
        return _path
