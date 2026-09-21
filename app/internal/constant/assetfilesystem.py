from __future__ import annotations

from enum import StrEnum


class AssetFilesystem(StrEnum):
    """
    Enumeration of supported storage platforms for assets.

    Values:
        LOCAL: Local file system storage.
        OSS: Alibaba Cloud OOS.

    """

    LOCAL = "local"
    OSS = "oss"
