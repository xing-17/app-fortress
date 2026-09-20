from __future__ import annotations

from enum import StrEnum


class SourceBoard(StrEnum):
    """
    Source boards for different categories.

    Attributes:
        FINANCE (str): Finance-related source board.
        MACRO (str): Macro Economic-related source board.

    """

    FINANCE = "finance"
    MACRO = "macro"
