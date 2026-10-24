from __future__ import annotations


class NodeSourceNotFoundError(LookupError):
    """Source does not exist on this node"""


class NodeDatasetNotFoundError(LookupError):
    """Dataset does not exist on this node"""


class NodeRunNotFoundError(LookupError):
    """Dataset run does not exist on this node"""


class NodeBusyError(RuntimeError):
    """Node cannot take the dataset run now, the caller may retry later"""


class NodeBadRequestError(ValueError):
    """Bad request made to this node"""


class NodeUnauthorizedError(PermissionError):
    """Unauthorized request made to this node"""


class NodeUnknownError(RuntimeError):
    """Unknown error occurred on this node"""


class NodeUnavailableError(ConnectionError):
    """Node cannot be reached or did not answer in time"""
