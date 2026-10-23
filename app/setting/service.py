from __future__ import annotations

import math
import re
from datetime import date
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator

from app.internal.abstract.setting import IAbstractSetting, IAbstractTaggedSetting
from app.internal.constant.servicekind import ServiceKind
from app.setting._log import LogSetting

# No wildcard, scheme or path: a Host header is a name with an optional port
_HOST_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*(:[0-9]{1,5})?\Z")

# Snapshots live in memory, this keeps a mistyped interval from eating it
_MAX_SNAPSHOTS = 10_000


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
        interval_seconds (int): Seconds between two snapshots
        retention_hours (float): How far back snapshots are kept, older ones are dropped
        max_snapshots (int): Snapshots kept at most, derived from the two above

    """

    kind: Literal[ServiceKind.MACHINE] = ServiceKind.MACHINE
    interval_seconds: int = Field(
        default=60,
        description="[Optional] Seconds between two snapshots",
        ge=1,
    )
    retention_hours: float = Field(
        default=12.0,
        description="[Optional] How far back snapshots are kept in hours",
        gt=0,
    )

    @property
    def max_snapshots(self) -> int:
        return math.ceil(self.retention_hours * 3600 / self.interval_seconds)

    @model_validator(mode="after")
    def _validate_max_snapshots(self):
        if self.max_snapshots > _MAX_SNAPSHOTS:
            _msg = f"machine: {self.max_snapshots} snapshots exceed {_MAX_SNAPSHOTS}, raise interval_seconds or lower retention_hours"
            raise ValueError(_msg)
        return self


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
        refresh_interval_seconds (float):
            Min time between two credential refreshes of a session, 0 refreshes before every query

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
    refresh_interval_seconds: float = Field(
        default=120.0,
        ge=0,
        description="[Optional] Min time between two credential refreshes of a session, 0 refreshes before every query",
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
        delegate (bool): May act for another caller named in the `X-Fortress-Caller` header,
            only for a host service that has already authenticated that caller

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
    delegate: bool = Field(
        default=False,
        description="[Optional] Whether the token may act for a caller named in X-Fortress-Caller",
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
        token (SecretStr | None): Bearer token of this host on the node (`fortress auth show <name>`),
            held as SecretStr so repr and export never show it

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
    token: SecretStr | None = Field(
        default=None,
        description="[Optional] Bearer token of this host on the node",
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


class AccessUserSetting(IAbstractSetting):
    """
    One person allowed through Cloudflare Access

    Attributes:
    ----------
        email (str): Email of the identity Access verified, compared in lowercase
        name (str): Caller name in the logs and on the node, same shape as a token name

    """

    email: str = Field(
        ...,
        description="Email of the identity verified by Access",
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    name: str = Field(
        ...,
        description="Caller name",
        pattern=r"^[a-z0-9][a-z0-9-]{0,31}$",
    )

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        return value.lower()


class AccessSetting(IAbstractSetting):
    """
    Cloudflare Access in front of the host, it signs who the caller is in `Cf-Access-Jwt-Assertion`

    Attributes:
    ----------
        team_domain (str): Team domain of the Zero Trust organization, `<team>.cloudflareaccess.com`
        audience (str): AUD tag of the Access application, a token minted for another application is rejected
        users (list[AccessUserSetting]): The identities allowed in, everyone else is rejected even when
            Access let them through

    """

    team_domain: str = Field(
        ...,
        description="Team domain, <team>.cloudflareaccess.com",
        pattern=r"^[a-z0-9][a-z0-9-]*\.cloudflareaccess\.com$",
    )
    audience: str = Field(
        ...,
        description="AUD tag of the Access application",
        min_length=16,
    )
    users: list[AccessUserSetting] = Field(
        ...,
        description="Identities allowed in",
        min_length=1,
    )

    @field_validator("team_domain")
    @classmethod
    def _lowercase_domain(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def _validate_users(self):
        _emails = [u.email for u in self.users]
        if len(_emails) != len(set(_emails)):
            raise ValueError(f"access: duplicate user emails: {_emails}")
        return self


class McpHostServiceSetting(AbstractHostServiceSetting):
    """
    MCP host service setting, MCP adapter in front of nodes

    Attributes:
    ----------
        kind (Literal[ServiceKind.MCPHOST]): Service kind, fixed as MCPHOST
        host (str): Listen host, loopback by default
        port (int): Listen port
        public_hosts (list[str]): Host names (optionally with port) clients reach this host by through a
            tunnel or proxy, the Host header of a request must be one of them or loopback
        auth (AuthSetting): Bearer tokens of the users of this host, one per device
        access (AccessSetting | None): Cloudflare Access in front of the host, when set a request carrying
            an Access assertion is authenticated by it, a request without one still needs a bearer token

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
    public_hosts: list[str] = Field(
        default_factory=list,
        description="[Optional] Host names clients reach this host by through a tunnel or proxy",
    )
    auth: AuthSetting = Field(
        default_factory=lambda: AuthSetting(masterfile="../local/.auth/mcphost.key"),
        description="[Optional] Bearer tokens of the users, its master key must not be the node's",
    )
    access: AccessSetting | None = Field(
        default=None,
        description="[Optional] Cloudflare Access in front of the host",
    )

    @field_validator("public_hosts")
    @classmethod
    def _validate_public_hosts(cls, value: list[str]) -> list[str]:
        _hosts: list[str] = []
        for _host in value:
            # Lowercase because browsers and proxies send the Host header lowercased
            _name: str = _host.strip().lower()
            if not _HOST_PATTERN.match(_name):
                raise ValueError(f"public_hosts: '{_host}' is not a host name, use 'name' or 'name:port'")
            if _name not in _hosts:
                _hosts.append(_name)
        return _hosts


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
