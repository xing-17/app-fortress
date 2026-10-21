from __future__ import annotations

from typing import ClassVar

from app.internal.constant.platform import Platform
from app.resource.identity._common._secret import BaseSecret


class LocalSecret(BaseSecret):
    """
    Local secret, always empty (for granularity only)

    Attributes:
    ----------
        platform (Platform):
            Platform type, fixed as Platform.LOCAL

    Example:
    ----------
        >>> secret = LocalSecret()

    """

    # Enforced public class variables
    platform: ClassVar[Platform] = Platform.LOCAL
