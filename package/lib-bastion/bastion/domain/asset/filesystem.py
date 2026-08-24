from __future__ import annotations

from enum import StrEnum


class AssetFilesystem(StrEnum):
    """
    Enumeration of supported storage platforms for assets.

    Values:
        LOCAL: Local file system storage.
        AWS_S3: Amazon S3 cloud storage.
        ALIYUN_OSS: Alibaba Cloud Object Storage Service.

    """

    LOCAL = "local"
    AWS_S3 = "aws_s3"
    ALIYUN_OSS = "aliyun_oss"
