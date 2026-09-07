from __future__ import annotations


from app.internal.abstract.setting import IAbstractSetting
from pydantic import Field


class SystemSetting(IAbstractSetting):
    """
    System configuration settings.

    Attributes:
        timezone: str | None = None
            系统时区

    """

    timezone: str | None = Field(
        default=None,
        description="系统时区",
    )
