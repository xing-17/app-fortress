from __future__ import annotations

from enum import StrEnum


class AssetKind(StrEnum):
    """
    Enumeration of supported asset file formats.

    Values:
        PARQUET: Parquet columnar storage format.
        CSV: Comma-separated values format.
        
    """
    
    PARQUET = "parquet"
    CSV = "csv"
