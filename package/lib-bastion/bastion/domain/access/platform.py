from __future__ import annotations

from enum import StrEnum


class AccessPlatform(StrEnum):
    """
    Enumeration of supported access kinds.

    Values:
        LOCAL: Local access kind.
        AWS: Amazon Web Services access kind.
        ALIYUN: Alibaba Cloud access kind.

    """

    LOCAL = "local"
    AWS = "aws"
    ALIYUN = "aliyun"
