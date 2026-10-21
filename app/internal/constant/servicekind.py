from __future__ import annotations

from enum import StrEnum


class ServiceKind(StrEnum):
    """
    Enumeration of the fortress services

    Values:
    ----------
        MACHINE: Host machine status (disk, memory, cpu)
        NODE: Data node, the core service (catalog, schema, quality, query)
        MCPHOST: MCP adapter in front of a node
        WEBHOST: Web adapter in front of a node

    """

    MACHINE = "machine"
    NODE = "node"
    MCPHOST = "mcphost"
    WEBHOST = "webhost"
