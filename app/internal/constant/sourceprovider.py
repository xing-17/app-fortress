from __future__ import annotations

from enum import StrEnum


class SourceProvider(StrEnum):
    """
    Source provider, used to locate runtime data sources.

    Values:
    ----------
        TUSHARE: China Tushare (3rd party).
        NSW_VG: New South Wales Valuer General (government).
        ABS: Australia ABS (government).

    """

    TUSHARE = "tushare"
    NSW_VG = "nsw_vg"
    ABS = "abs"


class SourceProviderType(StrEnum):
    """
    Source provider type.

    Values:
    ----------
        ORG: 3rd party organization.
        GOV: Government.

    """

    ORG = "org"
    GOV = "gov"
