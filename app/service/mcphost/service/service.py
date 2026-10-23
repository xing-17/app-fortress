from __future__ import annotations

from collections.abc import Mapping
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
    MCP host, lets an AI client list, inspect and query the datasets of its nodes

    The host holds no data and no logic of its own: every tool is answered by a `NodeClient`.
    A host serves every node of `setting.nodes`, or only the one `node` names.
    Starting needs at least one node that answers, runs and accepts the token, so a wrong endpoint
    or token on every node fails the start. A node that is down at start or later is reported by
    `list_nodes` and does not stop the others.

    The MCP route needs a bearer token of `setting.auth` (one per device). The host names the user
    of each query to the node, which runs it in a session of its own and audits it by name.

    Args:
    ----------
        setting (McpHostServiceSetting):
            MCP host service setting
        node (str | None):
            Name of the only node in `setting.nodes` to serve, defaults to all of them
        clients (Mapping[str, NodeClient] | None):
            Ready-made clients by node name, a node without one gets an `HttpNodeClient` of its
            setting, a given client is not closed by the service
        auth (TokenAuth | None):
            Verifier of the user tokens, required by `asgi_app`
        access (AccessAuth | None):
            Verifier of the Cloudflare Access assertion, defaults to one built from `setting.access`
            when that is set. A request carrying the assertion is authenticated by it alone.

    Attributes:
    ----------
        nodes (list[NodeEndpointSetting]):
            The nodes this host serves

    Methods:
    ----------
        asgi_app(host=None) -> Starlette:
            The streamable HTTP application of the MCP server, the service must be running
        health() -> dict:
            Service state and whether each node answers

    """

    kind = ServiceKind.MCPHOST

    def __init__(
        self,
        setting: McpHostServiceSetting,
        node: str | None = None,
        clients: Mapping[str, NodeClient] | None = None,
        auth: TokenAuth | None = None,
        access: AccessAuth | None = None,
    ) -> None:
        super().__init__(setting)
        self._nodes: list[NodeEndpointSetting] = self._select_nodes(setting, node)
        self._injected: dict[str, NodeClient] = dict(clients or {})
        _node_names: set[str] = {s.name for s in setting.nodes}

        # Check that all injected clients correspond to known nodes
        _unknown: list[str] = []
        for _n in self._injected:
            if _n not in _node_names:
                _unknown.append(_n)

        if _unknown:
            _msg: str = f"clients for nodes {_unknown} that are not in the setting"
            raise ValueError(_msg)

        self._clients: dict[str, NodeClient] = {}
        self._owned: list[NodeClient] = []
        self._auth: TokenAuth | None = auth
        if access is None and setting.access is not None:
            access = AccessAuth(setting.access)
        self._access: AccessAuth | None = access
        self._server: MCPServer | None = None

    @property
    def nodes(self) -> list[NodeEndpointSetting]:
        return list(self._nodes)

    @staticmethod
    def _select_nodes(
        setting: McpHostServiceSetting,
        name: str | None,
    ) -> list[NodeEndpointSetting]:
        if name is None:
            return list(setting.nodes)
        for _node in setting.nodes:
            if _node.name == name:
                return [_node]
        _names: list[str] = [n.name for n in setting.nodes]
        _msg: str = f"node '{name}' is not in the setting, known nodes: {_names}"
        raise ValueError(_msg)

    def _start(self) -> None:
        try:
            for _node in self._nodes:
                _client: NodeClient | None = self._injected.get(_node.name)
                if _client is None:
                    _client = HttpNodeClient.from_setting(_node)
                    self._owned.append(_client)
                self._clients[_node.name] = _client

            _errors: list[Exception] = []
            for _name, _client in self._clients.items():
                try:
                    self._check(_name, _client)
                except Exception as e:
                    # A node that is down now may be back later, only all of them down fails the start
                    self.log.warning(
                        f"node not available at start: {_name}",
                        metadata={"node": _name, "error": type(e).__name__},
                    )
                    _errors.append(e)
            if len(_errors) == len(self._clients):
                raise _errors[0]
            self._server: MCPServer = build_server(self._clients, self.log)
        except BaseException:
            self._release()
            raise

    @staticmethod
    def _check(
        name: str,
        client: NodeClient,
    ) -> None:
        _health: dict[str, Any] = client.health()
        if not _health.get("is_running"):
            _msg: str = f"node '{name}' is not running, state is {_health.get('state')}"
            raise RuntimeError(_msg)
        # The health route needs no token
        # so this is what proves the token works
        client.list_sources()

    def _stop(self) -> None:
        self._server = None
        self._release()

    def _release(self) -> None:
        for _client in self._owned:
            _client.close()
        self._owned = []
        self._clients = {}

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
        _nodes: list[dict[str, Any]] = []
        for _node in self._nodes:
            _entry: dict[str, Any] = {"name": _node.name, "reachable": False}
            _client: NodeClient | None = self._clients.get(_node.name)
            if _client is not None:
                try:
                    _entry["state"] = _client.health().get("state")
                    _entry["reachable"] = True
                except Exception:
                    pass
            _nodes.append(_entry)
        _res["nodes"] = _nodes
        return _res
