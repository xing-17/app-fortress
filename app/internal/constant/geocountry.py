from __future__ import annotations

from enum import StrEnum


class GeoCountry(StrEnum):
    """
    Geographic country codes.

    Values:
    ----------
        CN: China.
        AU: Australia.
        GLOBAL: Global.

    """

    CN = "CN"
    AU = "AU"

    # Globally applicable
    GLOBAL = "GLOBAL"
