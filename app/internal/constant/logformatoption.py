from __future__ import annotations

from enum import StrEnum


class LogFormatOption(StrEnum):
    """
    Log format Options

    Attributes:
        TEXT: str = "TEXT" 纯文本格式
        COLORTEXT: str = "COLORTEXT" 彩色文本格式
        TREE: str = "TREE" 树形结构格式
        COLORTREE: str = "COLORTREE" 彩色树形结构格式

    """

    TEXT = "TEXT"
    COLORTEXT = "COLORTEXT"
    TREE = "TREE"
    COLORTREE = "COLORTREE"
