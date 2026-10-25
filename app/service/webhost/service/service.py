from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware

from app.internal.constant.servicekind import ServiceKind
from app.service._common._service import BaseService
from app.service._common.access import AccessAuth
from app.service._common.auth import TokenAuth
from app.service.node.client.httpnode import HttpNodeClient
from app.service.node.client.node import NodeClient
from app.service.webhost.service.auth import (
    SecurityHeadersMiddleware,
    SessionStore,
    WebAuthMiddleware,
)
from app.service.webhost.service.pages import WebPages
from app.setting.service import NodeEndpointSetting, WebHostServiceSetting


class WebHostService(BaseService[WebHostServiceSetting]):
    """
    Web console of the nodes: which nodes there are, their sources and datasets, run a dataset, query

    The host holds no data and no logic of its own, every page is answered by a `NodeClient`.
    Starting does not need a node to answer, a node that is down shows as unreachable on the overview.

    A person signs in with the Cloudflare Access identity (`setting.access`) or by pasting a token of
    `setting.auth` into the login page. The host itself is one identity on each node (its own token,
    which must not delegate), so all queries of the console share one DRA session there, and the
    people are told apart in the log of this host.

    Args:
    ----------
        setting (WebHostServiceSetting):
            Web host service setting
        clients (Mapping[str, NodeClient] | None):
            Ready-made clients by node name, a node without one gets an `HttpNodeClient` of its
            setting, a given client is not closed by the service
        auth (TokenAuth | None):
            Verifier of the tokens of the login page, required by `asgi_app`
        access (AccessAuth | None):
            Verifier of the Cloudflare Access assertion, defaults to one built from `setting.access`

    Methods:
    ----------
        asgi_app() -> Starlette:
            The web application, the service must be running
        health() -> dict:
            Service state and the nodes it serves

    """

    kind = ServiceKind.WEBHOST

    def __init__(
        self,
        setting: WebHostServiceSetting,
        clients: Mapping[str, NodeClient] | None = None,
        auth: TokenAuth | None = None,
        access: AccessAuth | None = None,
    ) -> None:
        super().__init__(setting)
        self._injected: dict[str, NodeClient] = dict(clients or {})
        _known: set[str] = {n.name for n in setting.nodes}
        _unknown: list[str] = [n for n in self._injected if n not in _known]
        if _unknown:
            _msg: str = f"clients for nodes {_unknown} that are not in the setting"
            raise ValueError(_msg)

        self._auth: TokenAuth | None = auth
        if access is None and setting.access is not None:
            access = AccessAuth(setting.access)
        self._access: AccessAuth | None = access
        self._clients: dict[str, NodeClient] = {}
        self._owned: list[NodeClient] = []
        self._pool: ThreadPoolExecutor | None = None
        self._sessions: SessionStore = SessionStore()

    @property
    def nodes(self) -> list[NodeEndpointSetting]:
        return list(self.setting.nodes)

    def _start(self) -> None:
        try:
            for _node in self.setting.nodes:
                _client: NodeClient | None = self._injected.get(_node.name)
                if _client is None:
                    _client = HttpNodeClient.from_setting(_node)
                    self._owned.append(_client)
                self._clients[_node.name] = _client

            # One probe per node at a time on the overview
            # a few more for a node that does not answer
            self._pool = ThreadPoolExecutor(
                max_workers=max(4, 2 * len(self._clients)),
                thread_name_prefix="web-probe",
            )
        except BaseException:
            self._release()
            raise

    def _stop(self) -> None:
        self._release()

    def _release(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
        for _client in self._owned:
            _client.close()
        self._owned = []
        self._clients = {}

    def asgi_app(self) -> Starlette:
        if self._pool is None:
            _msg: str = f"{self.kind} is not running, state is {self.state}"
            raise RuntimeError(_msg)
        if self._auth is None:
            _msg: str = f"{self.kind} has no auth, it would serve the data to anyone"
            raise RuntimeError(_msg)

        _pages = WebPages(
            nodes=self.setting.nodes,
            clients=self._clients,
            auth=self._auth,
            sessions=self._sessions,
            log=self.log,
            pool=self._pool,
            display_timezone=self.setting.display_timezone,
        )
        return Starlette(
            routes=_pages.routes(),
            exception_handlers=_pages.exception_handlers(),
            middleware=[
                Middleware(SecurityHeadersMiddleware),
                Middleware(
                    WebAuthMiddleware,
                    sessions=self._sessions,
                    log=self.log,
                    public_hosts=frozenset(self.setting.public_hosts),
                    access=self._access,
                ),
            ],
        )

    def health(self) -> dict:
        _res: dict = super().health()
        _nodes: list[dict[str, Any]] = []
        for _node in self.setting.nodes:
            _content: dict[str, Any] = {
                "name": _node.name,
                "endpoint": _node.endpoint,
            }
            _nodes.append(_content)
        _res["nodes"] = _nodes
        return _res
