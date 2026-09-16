from __future__ import annotations

from enum import StrEnum


class AliyunIdentityType(StrEnum):
    """
    阿里云Identity类型枚举

    Values:
        CHAIN: 链式身份类型, 不传入任何配置参数
        AK: 使用Access Key进行身份验证

    """

    CHAIN = "chain"
    AK = "ak"
