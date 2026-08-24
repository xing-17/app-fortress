from __future__ import annotations

from abc import ABC
from typing import ClassVar

from pydantic import Field

from bastion.domain.access.platform import AccessPlatform
from bastion.internal.idomain import IDomain


class AbstractAccessDomain(IDomain, ABC):
    """
    Abstract base class for access profiles.

    Attributes:
        name: Name of the access profile.
        platform: Platform of the access profile.
        tags: Tags associated with the access profile.

    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        default="default",
        description="Access profile name",
    )
    platform: AccessPlatform = Field(
        default=AccessPlatform.LOCAL,
        description="Access platform of the profile",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the access profile",
    )
