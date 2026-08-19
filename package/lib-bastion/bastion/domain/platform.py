from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """
    Enumeration of supported storage platforms for assets.

    Attributes:
        S3 (str): Amazon S3 cloud storage.
        LOCAL (str): Local file system storage.
        OSS (str): Alibaba Cloud Object Storage Service.

    """

    LOCAL = "local"
    S3 = "s3"
    OSS = "oss"
