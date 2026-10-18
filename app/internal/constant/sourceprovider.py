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
    NSWVG = "nswvg"
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


class SourceFetchType(StrEnum):
    """
    Source fetch type.

    Values:
    ----------
        AUTOMATIC: Automatically fetch the source.
        PROVISION: Provision the source manually.

    """

    AUTOMATIC: str = "automatic"
    PROVISION: str = "provision"
