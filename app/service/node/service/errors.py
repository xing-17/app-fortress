from __future__ import annotations


class NodeSourceNotFoundError(LookupError):
    """Source does not exist on this node"""


class NodeDatasetNotFoundError(LookupError):
    """Dataset does not exist on this node"""


class NodeBadRequestError(ValueError):
    """Bad request made to this node"""


class NodeUnauthorizedError(PermissionError):
    """Unauthorized request made to this node"""


class NodeUnknownError(RuntimeError):
    """Unknown error occurred on this node"""
