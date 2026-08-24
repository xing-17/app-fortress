from __future__ import annotations

from enum import StrEnum


class AssetObjectkind(StrEnum):
    """
    Enumeration of supported asset object kinds.

    Values:
        PARQUET: Parquet columnar storage format.
        CSV: Comma-separated values format.
        OBJECT: Generic object type for any other asset kind.

    """

    PARQUET = "parquet"
    CSV = "csv"

    # fall back for any other object type
    OBJECT = "object"
