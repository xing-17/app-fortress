from __future__ import annotations

from enum import StrEnum


class AssetKind(StrEnum):
    """
    Enumeration of supported asset file formats.

    Attributes:
        PARQUET (str): Parquet columnar storage format.
        CSV (str): Comma-separated values format.
        ANY (str): Any asset format.

    """

    PARQUET = "parquet"
    CSV = "csv"
    ANY = "any"
