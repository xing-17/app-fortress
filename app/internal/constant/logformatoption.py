from __future__ import annotations

from enum import StrEnum


class LogFormatOption(StrEnum):
    """
    Log format Options

    Attributes:
        TEXT: str = "TEXT" plain text format
        COLORTEXT: str = "COLORTEXT" colored text format
        TREE: str = "TREE" tree-structured format
        COLORTREE: str = "COLORTREE" colored tree-structured format

    """

    TEXT = "TEXT"
    COLORTEXT = "COLORTEXT"
    TREE = "TREE"
    COLORTREE = "COLORTREE"
