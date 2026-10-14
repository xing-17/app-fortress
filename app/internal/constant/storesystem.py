from __future__ import annotations

from enum import StrEnum


class StoreSystem(StrEnum):
    """
    Enumeration of supported store systems

    Values:
    ----------
        FILE: JSON file-based store system
        OSS: Aliyun Object Storage Service-based store system

    """

    FILE = "file"
    OSS = "oss"
