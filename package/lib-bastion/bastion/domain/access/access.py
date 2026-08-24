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
        name (str): Name of the access profile.
        platform (AccessPlatform): Platform of the access profile.
        tags (dict[str, str]): Tags associated with the access profile.

    Methods:
        from_dict(value): Convert dict or instance to access model (inherited).
        export(): Export the access model as a dictionary (inherited).
        describe(): Export access as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).

    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Access profile name",
    )
    platform: AccessPlatform = Field(
        AccessPlatform.LOCAL,
        description="Access platform of the profile",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the access profile",
    )
