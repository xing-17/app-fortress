from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from app.internal.constant.servicekind import ServiceKind
from app.service._common._service import BaseService
from app.service._common.access import AccessAuth
from app.service._common.auth import TokenAuth
from app.service._common.http import BearerAuthMiddleware
from app.service.mcphost.service.tools import build_server
from app.service.node.client.httpnode import HttpNodeClient
from app.service.node.client.node import NodeClient
from app.setting.service import McpHostServiceSetting, NodeEndpointSetting

_LOCAL_HOSTS: tuple[str, ...] = (
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
)
_LOCAL_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)


class McpHostService(BaseService[McpHostServiceSetting]):
    """
    MCP host, lets an AI client list, inspect and query the datasets of one node

    The host holds no data and no logic of its own: every tool is answered by a `NodeClient`.
    A host talks to one node, the first of `setting.nodes` unless `node` names another.
    Starting checks that the node answers and runs and accepts the token, so a wrong endpoint or
    token fails the start.

    The MCP route needs a bearer token of `setting.auth` (one per device). The host names the user
    of each query to the node, which runs it in a session of its own and audits it by name.

    Args:
    ----------
        setting (McpHostServiceSetting):
            MCP host service setting
        node (str | None):
            Name of the node in `setting.nodes`, defaults to the first
        client (NodeClient | None):
            Ready-made client, defaults to an `HttpNodeClient` of the node setting,
            a given client is not closed by the service
        auth (TokenAuth | None):
            Verifier of the user tokens, required by `asgi_app`
        access (AccessAuth | None):
            Verifier of the Cloudflare Access assertion, defaults to one built from `setting.access`
            when that is set. A request carrying the assertion is authenticated by it alone.

    Attributes:
    ----------
        node (NodeEndpointSetting):
            The node this host talks to

    Methods:
    ----------
        asgi_app(host=None) -> Starlette:
            The streamable HTTP application of the MCP server, the service must be running
        health() -> dict:
            Service state and whether the node answers

    """

    kind = ServiceKind.MCPHOST

    def __init__(
        self,
        setting: McpHostServiceSetting,
        node: str | None = None,
        client: NodeClient | None = None,
        auth: TokenAuth | None = None,
        access: AccessAuth | None = None,
    ) -> None:
        super().__init__(setting)
        self._node: NodeEndpointSetting = self._select_node(setting, node)
        self._client: NodeClient | None = client
        self._auth: TokenAuth | None = auth
        if access is None and setting.access is not None:
            access = AccessAuth(setting.access)
        self._access: AccessAuth | None = access
        self._owns_client: bool = client is None
        self._server: MCPServer | None = None

    @property
    def node(self) -> NodeEndpointSetting:
        return self._node

    @staticmethod
    def _select_node(
        setting: McpHostServiceSetting,
        name: str | None,
    ) -> NodeEndpointSetting:
        if name is None:
            return setting.nodes[0]
        for _node in setting.nodes:
            if _node.name == name:
                return _node
        _names: list[str] = [n.name for n in setting.nodes]
        _msg: str = f"node '{name}' is not in the setting, known nodes: {_names}"
        raise ValueError(_msg)

    def _start(self) -> None:
        if self._client is None:
            self._client: HttpNodeClient = HttpNodeClient.from_setting(self._node)
        try:
            _health: dict[str, Any] = self._client.health()
            if not _health.get("is_running"):
                _msg: str = f"node '{self._node.name}' is not running, state is {_health.get('state')}"
                raise RuntimeError(_msg)
            # The health route needs no token
            # so this is what proves the token works
            self._client.list_sources()
            self._server: MCPServer = build_server(self._client, self.log)
        except BaseException:
            self._release()
            raise

    def _stop(self) -> None:
        self._server = None
        self._release()

    def _release(self) -> None:
        if self._client is not None and self._owns_client:
            self._client.close()
        if self._owns_client:
            self._client = None

    def asgi_app(
        self,
        host: str | None = None,
    ) -> Starlette:
        if self._server is None:
            _msg: str = f"{self.kind} is not running, state is {self.state}"
            raise RuntimeError(_msg)
        if self._auth is None:
            _msg: str = f"{self.kind} has no auth, it would serve the data to anyone"
            raise RuntimeError(_msg)
        # The transport rejects any Host or Origin that is neither loopback nor a public host
        _public: list[str] = list(self.setting.public_hosts)
        _allowed_hosts: list[str] = [
            *_LOCAL_HOSTS,  # Include local hosts for development and loopback access
            *_public,  # Include public hosts specified in the setting
        ]
        _allowed_origins: list[str] = [
            *_LOCAL_ORIGINS,  # Include local origins for development and loopback access
            *(f"https://{_h}" for _h in _public),  # Include public hosts specified in the setting
        ]
        _security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=_allowed_hosts,
            allowed_origins=_allowed_origins,
        )
        _app: Starlette = self._server.streamable_http_app(
            host=host or self.setting.host,
            transport_security=_security,
        )
        _app.add_middleware(
            BearerAuthMiddleware,
            auth=self._auth,
            log=self.log,
            public_paths=frozenset(),
            access=self._access,
        )
        return _app

    def health(self) -> dict:
        _res: dict = super().health()
        _node: dict[str, Any] = {
            "name": self._node.name,
            "reachable": False,
        }
        if self._client is not None:
            try:
                _node["state"] = self._client.health().get("state")
                _node["reachable"] = True
            except Exception:
                pass
        _res["node"] = _node
        return _res
