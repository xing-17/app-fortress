from __future__ import annotations

from enum import StrEnum


class AssetFileKind(StrEnum):
    """
    Enumeration of supported file kinds for assets.

    Values:
    ----------
        PARQUET: Parquet files.
        OBJECT: Generic object files.

    """

    PARQUET = "parquet"
    OBJECT = "object"
