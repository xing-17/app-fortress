from __future__ import annotations

from enum import StrEnum


class AliyunAccessType(StrEnum):
    """
    阿里云Access类型枚举

    Values:
        CHAIN: 链式访问类型, 不传入任何配置参数
        AK: 使用Access Key进行访问

    """

    CHAIN = "chain"
    AK = "ak"
