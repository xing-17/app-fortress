from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.internal.abstract.setting import IAbstractSetting, IAbstractTaggedSetting
from app.internal.constant.servicekind import ServiceKind
from app.setting._log import LogSetting


class AbstractServiceSetting(IAbstractTaggedSetting):
    """
    Abstract service setting

    Attributes:
    ----------
        kind (ServiceKind): Service kind, fixed by each concrete setting
        enabled (bool): Whether the service is enabled
        log (LogSetting | None): Log configuration, defaults to
            console plus ./local/.logs/service/<kind>.log
        tags (dict[str, str]): Service tags

    """

    kind: ServiceKind = Field(
        ...,
        description="[discriminator] Service kind",
    )
    enabled: bool = Field(
        default=True,
        description="[Optional] Whether the service is enabled",
    )
    log: LogSetting | None = Field(
        default=None,
        description="[Optional] Log configuration of the service",
    )
    # [Inherited]: tags (dict[str, str])

    def _non_override_tags(self) -> dict[str, str]:
        return {"kind": self.kind}

    @model_validator(mode="after")
    def _derive_log(self):
        if self.log is None:
            _log = LogSetting(
                name=str(self.kind),
                tags={"service": str(self.kind)},
                file_path="./local/.logs/service",
            )
            object.__setattr__(self, "log", _log)
        return self


class MachineServiceSetting(AbstractServiceSetting):
    """
    Machine service setting, host machine status (disk, memory, cpu)

    Attributes:
    ----------
        kind (Literal[ServiceKind.MACHINE]): Service kind, fixed as MACHINE

    """

    kind: Literal[ServiceKind.MACHINE] = ServiceKind.MACHINE


class DRASetting(IAbstractSetting):
    """
    Query sandbox limits of the node

    Attributes:
    ----------
        timeout_seconds (float):
            Wall-clock limit of one query, the query is interrupted when exceeded
        max_rows (int):
            Row cap of one result, extra rows are dropped and the result is marked truncated
        max_result_mb (float):
            Size cap of one result in MB, extra rows are dropped and the result is marked truncated
        memory_limit_mb (int):
            Memory limit of the query engine, queries exceeding it fail
        threads (int):
            Worker threads of the query engine
        max_sessions (int):
            Max concurrent sessions, one per caller, the least recently used idle one is evicted
        max_session_idle_seconds (float):
            Max idle time before a session is closed, 0 disables

    """

    # Single query settings
    timeout_seconds: float = Field(
        default=30.0,
        description="[Optional] Wall-clock limit of one query in seconds",
        gt=0,
    )
    max_rows: int = Field(
        default=10_000,
        description="[Optional] Row cap of one result",
        ge=1,
    )
    max_result_mb: float = Field(
        default=128.0,
        description="[Optional] Size cap of one result in MB",
        gt=0,
    )
    memory_limit_mb: int = Field(
        default=1024,
        description="[Optional] Memory limit of the query engine in MB",
        ge=16,
    )
    threads: int = Field(
        default=4,
        description="[Optional] Worker threads of the query engine",
        ge=1,
    )

    # Group session settings
    max_sessions: int = Field(default=4, ge=1, description="[Optional] Max concurrent sessions")
    max_session_idle_seconds: float = Field(
        default=900.0, ge=0, description="[Optional] Max idle time before a session is closed, 0 disables"
    )


class TokenSetting(IAbstractSetting):
    """
    One access token entry, the token itself is derived from the master key and never stored

    Attributes:
    ----------
        name (str): Token name, lowercase letters, digits and '-', used to derive the token
        description (str): What the token is for
        version (int): Bump to invalidate the current token and derive a new one
        expires (date | None): Last valid day (UTC), None means never expires
        revoked (bool): Revoked tokens are always rejected

    """

    name: str = Field(
        ...,
        description="Token name",
        pattern=r"^[a-z0-9][a-z0-9-]{0,31}$",
    )
    description: str = Field(
        default="",
        description="[Optional] What the token is for",
    )
    version: int = Field(
        default=1,
        description="[Optional] Bump to rotate the token",
        ge=1,
    )
    expires: date | None = Field(
        default=None,
        description="[Optional] Last valid day (UTC)",
    )
    revoked: bool = Field(
        default=False,
        description="[Optional] Whether the token is revoked",
    )


class AuthSetting(IAbstractSetting):
    """
    Node auth setting, bearer tokens derived from one master key

    Attributes:
    ----------
        masterfile (str): Master key file, relative paths are resolved against the settings directory
        tokens (list[TokenSetting]): Token entries, names must be unique

    """

    masterfile: str = Field(
        default="../local/.auth/password.key",
        description="[Optional] Master key file",
        min_length=1,
    )
    tokens: list[TokenSetting] = Field(
        default_factory=list,
        description="[Optional] Token entries",
    )

    @model_validator(mode="after")
    def _validate_tokens(self):
        _names = [t.name for t in self.tokens]
        if len(_names) != len(set(_names)):
            raise ValueError(f"auth: duplicate token names: {_names}")
        return self


class NodeServiceSetting(AbstractServiceSetting):
    """
    Node service setting, the data node (catalog, schema, quality, query)

    Attributes:
    ----------
        kind (Literal[ServiceKind.NODE]): Service kind, fixed as NODE
        host (str): Listen host, loopback by default
        port (int): Listen port
        dra (DRASetting): Query sandbox limits
        auth (AuthSetting): Bearer token auth

    """

    kind: Literal[ServiceKind.NODE] = ServiceKind.NODE
    host: str = Field(
        default="127.0.0.1",
        description="[Optional] Listen host",
    )
    port: int = Field(
        default=8800,
        description="[Optional] Listen port",
        ge=1,
        le=65535,
    )
    dra: DRASetting = Field(
        default_factory=DRASetting,
        description="[Optional] Query sandbox limits",
    )
    auth: AuthSetting = Field(
        default_factory=AuthSetting,
        description="[Optional] Bearer token auth",
    )


class NodeEndpointSetting(IAbstractSetting):
    """
    Endpoint of a node, as seen from a host service

    Attributes:
    ----------
        name (str): Node name, matches SystemSetting.node of that node
        endpoint (str): Base URL of the node service

    """

    name: str = Field(
        ...,
        description="Node name",
        min_length=1,
    )
    endpoint: str = Field(
        ...,
        description="Base URL of the node service",
        min_length=1,
    )


def _default_nodes() -> list[NodeEndpointSetting]:
    _default: NodeEndpointSetting = NodeEndpointSetting(
        name="centre",
        endpoint="http://127.0.0.1:8800",
    )
    return [_default]


class AbstractHostServiceSetting(AbstractServiceSetting):
    """
    Abstract host service setting, an adapter in front of one or more nodes

    Attributes:
    ----------
        nodes (list[NodeEndpointSetting]): Nodes this host talks to, names must be unique

    """

    nodes: list[NodeEndpointSetting] = Field(
        default_factory=_default_nodes,
        description="[Optional] Nodes this host talks to",
        min_length=1,
    )

    @model_validator(mode="after")
    def _validate_nodes(self):
        _names = [n.name for n in self.nodes]
        if len(_names) != len(set(_names)):
            raise ValueError(f"{self.kind}: duplicate node names: {_names}")
        return self


class McpHostServiceSetting(AbstractHostServiceSetting):
    """
    MCP host service setting, MCP adapter in front of nodes

    Attributes:
    ----------
        kind (Literal[ServiceKind.MCPHOST]): Service kind, fixed as MCPHOST
        host (str): Listen host, loopback by default
        port (int): Listen port

    """

    kind: Literal[ServiceKind.MCPHOST] = ServiceKind.MCPHOST
    host: str = Field(
        default="127.0.0.1",
        description="[Optional] Listen host",
    )
    port: int = Field(
        default=8801,
        description="[Optional] Listen port",
        ge=1,
        le=65535,
    )


class WebHostServiceSetting(AbstractHostServiceSetting):
    """
    Web host service setting, web adapter in front of nodes

    Attributes:
    ----------
        kind (Literal[ServiceKind.WEBHOST]): Service kind, fixed as WEBHOST
        host (str): Listen host, loopback by default
        port (int): Listen port

    """

    kind: Literal[ServiceKind.WEBHOST] = ServiceKind.WEBHOST
    host: str = Field(
        default="127.0.0.1",
        description="[Optional] Listen host",
    )
    port: int = Field(
        default=8802,
        description="[Optional] Listen port",
        ge=1,
        le=65535,
    )


class ServicesSetting(IAbstractSetting):
    """
    Services setting, the four fortress services keyed by kind (settings/services.yaml)

    Attributes:
    ----------
        machine (MachineServiceSetting): Machine service setting
        node (NodeServiceSetting): Node service setting
        mcphost (McpHostServiceSetting): MCP host service setting
        webhost (WebHostServiceSetting): Web host service setting

    """

    machine: MachineServiceSetting = Field(
        default_factory=MachineServiceSetting,
        description="[Optional] Machine service configuration",
    )
    node: NodeServiceSetting = Field(
        default_factory=NodeServiceSetting,
        description="[Optional] Node service configuration",
    )
    mcphost: McpHostServiceSetting = Field(
        default_factory=McpHostServiceSetting,
        description="[Optional] MCP host service configuration",
    )
    webhost: WebHostServiceSetting = Field(
        default_factory=WebHostServiceSetting,
        description="[Optional] Web host service configuration",
    )
