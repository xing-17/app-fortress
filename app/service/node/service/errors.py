from __future__ import annotations


class NodeSourceNotFoundError(LookupError):
    """Source does not exist on this node"""


class NodeDatasetNotFoundError(LookupError):
    """Dataset does not exist on this node"""


class NodeBusyError(RuntimeError):
    """Every session slot of this node is running a query"""
