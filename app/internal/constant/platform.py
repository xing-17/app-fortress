from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """
    Enumeration of supported platforms.

    Attributes:
        LOCAL: str = "local" 本地平台
        ALIYUN: str = "aliyun" 阿里云平台

    """

    LOCAL = "local"
    ALIYUN = "aliyun"
