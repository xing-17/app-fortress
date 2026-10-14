from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """
    Enumeration of supported platforms.

    Values:
    ----------
        LOCAL: str = "local" local platform
        ALIYUN: str = "aliyun" Aliyun platform

    """

    LOCAL = "local"
    ALIYUN = "aliyun"
