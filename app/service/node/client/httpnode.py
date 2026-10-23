from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import SecretStr

from app.internal.util.clock import IClock
from app.service.node.client.node import NodeClient
from app.service.node.dra import (
    DRABusyError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)
from app.service.node.dra.result import DRADataResult
from app.service.node.service.errors import (
    NodeBadRequestError,
    NodeDatasetNotFoundError,
    NodeSourceNotFoundError,
    NodeUnauthorizedError,
    NodeUnavailableError,
    NodeUnknownError,
)
from app.setting.service import NodeEndpointSetting

# Errors the node names in its response body, anything else is mapped by status
_NAMED_ERRORS: dict[str, type[Exception]] = {
    _type.__name__: _type
    for _type in (
        NodeSourceNotFoundError,
        NodeDatasetNotFoundError,
        NodeBadRequestError,
        DRARejectedError,
        DRAQueryError,
        DRAQueryTimeoutError,
        DRABusyError,
    )
}

_STATUS_ERRORS: dict[int, type[Exception]] = {
    400: NodeBadRequestError,
    401: NodeUnauthorizedError,
    408: DRAQueryTimeoutError,
    413: NodeBadRequestError,
    503: DRABusyError,
}


class HttpNodeClient(NodeClient):
    """
    `NodeClient` over the `/internal/...` HTTP routes of a node, authenticated by a bearer token

    The node decides who the caller is from the token, so all queries of one client share one
    DRA session on the node, unless `query` names a `caller` and the token may delegate:
    then each caller gets its own session. Responses are parsed back into the types the node
    raised or returned.

    Args:
    ----------
        endpoint (str):
            Base URL of the node, e.g. http://127.0.0.1:8800
        token (str | SecretStr):
            Bearer token, `fortress auth show <name>` on the node
        timeout_seconds (float):
            Timeout of one request, keep it above `dra.timeout_seconds` of the node so a slow
            query is answered by the node (408) and not cut off here
        client (httpx.Client | None):
            Ready-made HTTP client, for tests, the caller closes it

    Methods:
    ----------
        from_setting(setting, timeout_seconds=60.0) -> HttpNodeClient:
            Build from a `NodeEndpointSetting`, raises ValueError when it has no token

    """

    def __init__(
        self,
        endpoint: str,
        token: str | SecretStr,
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if isinstance(token, SecretStr):
            token = token.get_secret_value()
        _token: str = token
        _token = _token.strip()
        if not _token:
            raise ValueError("token must not be empty")

        self._endpoint: str = endpoint.rstrip("/")
        self._headers: dict[str, str] = {"Authorization": f"Bearer {_token}"}
        self._owns_client: bool = client is None
        self._client: httpx.Client = client or httpx.Client(
            base_url=self._endpoint,
            timeout=timeout_seconds,
        )

    @classmethod
    def from_setting(
        cls,
        setting: NodeEndpointSetting,
        timeout_seconds: float = 60.0,
    ) -> HttpNodeClient:
        if setting.token is None:
            raise ValueError(f"node '{setting.name}' has no token, set `token` in endpoint setting")
        return cls(
            endpoint=setting.endpoint,
            token=setting.token,
            timeout_seconds=timeout_seconds,
        )

    def __repr__(self) -> str:
        return f"HttpNodeClient(endpoint={self._endpoint!r})"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # --------------------------------------------------
    # Transport: Low-level HTTP transport utilities
    # --------------------------------------------------

    @staticmethod
    def _time(value: datetime | float) -> str:
        if isinstance(value, datetime):
            # A naive datetime would be read in the node's zone, so send it as UTC
            return IClock.from_datetime(value).isoformat()
        return str(value)

    @classmethod
    def _window(
        cls,
        since: datetime | float | None,
        until: datetime | float | None,
    ) -> dict[str, str]:
        _res: dict[str, str] = {}
        if since is not None:
            _res["since"] = cls._time(since)
        if until is not None:
            _res["until"] = cls._time(until)
        return _res

    @staticmethod
    def _segment(value: str) -> str:
        # Encode "/" too
        # a name must stay one path segment
        return quote(value, safe="")

    def _send(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            return self._client.request(
                method,
                path,
                params=params,
                json=body,
                headers={**self._headers, **(headers or {})},
            )
        except httpx.TimeoutException as e:
            raise NodeUnavailableError(f"node {self._endpoint} did not answer in time") from e
        except httpx.TransportError as e:
            raise NodeUnavailableError(f"node {self._endpoint} is unreachable: {type(e).__name__}") from e

    @staticmethod
    def _body(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    def _raise_for_error(
        self,
        response: httpx.Response,
    ) -> None:
        if response.is_success:
            return

        _body: Any = self._body(response)
        _name: Any = _body.get("error") if isinstance(_body, dict) else None
        _message: Any = _body.get("message") if isinstance(_body, dict) else None

        # Only the named errors carry a message meant for the caller
        if isinstance(_name, str):
            _type: type[Exception] | None = _NAMED_ERRORS.get(_name)
        else:
            _type = None

        if _type is not None and isinstance(_message, str):
            raise _type(_message)

        _type = _STATUS_ERRORS.get(response.status_code, NodeUnknownError)
        if _type is NodeUnauthorizedError:
            raise NodeUnauthorizedError(f"node {self._endpoint} rejected the token")
        raise _type(f"node {self._endpoint} answered {response.status_code}")

    def _call(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        _response: httpx.Response = self._send(
            method=method,
            path=path,
            params=params,
            body=body,
            headers=headers,
        )
        self._raise_for_error(_response)
        _res: Any = self._body(_response)
        if _res is None:
            raise NodeUnknownError(f"node {self._endpoint} answered a body that is not JSON")
        return _res

    # --------------------------------------------------
    # Catalog: Dataset and Source Catalog API
    # --------------------------------------------------

    def _dataset_path(
        self,
        source: str,
        dataset: str,
    ) -> str:
        _seg_source: str = self._segment(source)
        _seg_dataset: str = self._segment(dataset)
        return f"/internal/datasets/{_seg_source}/{_seg_dataset}"

    def list_sources(self) -> list[dict[str, Any]]:
        return self._call("GET", "/internal/sources")

    def get_source(
        self,
        source: str,
    ) -> dict[str, Any]:
        _source_seg: str = self._segment(source)
        _source_path: str = f"/internal/sources/{_source_seg}"
        return self._call(
            method="GET",
            path=_source_path,
        )

    def list_datasets(
        self,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        # List datasets from the node, optionally filtered by source
        if source is None:
            _params = None
        else:
            _params = {"source": source}

        return self._call(
            method="GET",
            path="/internal/datasets",
            params=_params,
        )

    def get_dataset(
        self,
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        # Get dataset information from the node via http request
        _dataset_path: str = self._dataset_path(source, dataset)
        return self._call(
            method="GET",
            path=_dataset_path,
        )

    def list_assetfiles(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        _dataset_path: str = self._dataset_path(source, dataset)
        return self._call(
            method="GET",
            path=f"{_dataset_path}/assetfiles",
            params=self._window(since, until),
        )

    def list_metadatas(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        _dataset_path: str = self._dataset_path(source, dataset)
        return self._call(
            method="GET",
            path=f"{_dataset_path}/metadatas",
            params=self._window(since, until),
        )

    def list_qualities(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        _dataset_path: str = self._dataset_path(source, dataset)
        return self._call(
            method="GET",
            path=f"{_dataset_path}/qualities",
            params=self._window(since, until),
        )

    def list_definitions(
        self,
        source: str,
        dataset: str,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
    ) -> list[dict[str, Any]]:
        _dataset_path: str = self._dataset_path(source, dataset)
        return self._call(
            method="GET",
            path=f"{_dataset_path}/definitions",
            params=self._window(since, until),
        )

    # --------------------------------------------------
    # DRA: Data Retrieval API
    # --------------------------------------------------

    def query(
        self,
        sql: str,
        caller: str | None = None,
    ) -> DRADataResult:
        _headers: dict[str, str] | None = None
        if caller is not None:
            _headers = {"X-Fortress-Caller": caller}
        _payload: Any = self._call(
            method="POST",
            path="/internal/query",
            body={"sql": sql},
            headers=_headers,
        )
        return DRADataResult.model_validate(_payload)

    # --------------------------------------------------
    # MACHINE: State of the host machine
    # --------------------------------------------------

    def list_machine_snapshots(
        self,
        hours: float | None = None,
    ) -> list[dict[str, Any]]:
        _params: dict[str, str] | None = None
        if hours is not None:
            _params = {"hours": str(hours)}
        return self._call(
            method="GET",
            path="/internal/machine/snapshots",
            params=_params,
        )

    # --------------------------------------------------
    # HEALTH: Check the health status of the node
    # --------------------------------------------------

    def health(self) -> dict[str, Any]:
        # 503 is a valid answer
        # it carries the state of a node that is not running
        _response: httpx.Response = self._send(
            method="GET",
            path="/health",
        )
        if _response.status_code not in (200, 503):
            self._raise_for_error(_response)
        _res: Any = self._body(_response)
        if not isinstance(_res, dict):
            raise NodeUnknownError(f"node {self._endpoint} answered a health body that is not JSON")
        return _res
