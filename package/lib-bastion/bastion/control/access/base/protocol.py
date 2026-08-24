from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bastion.domain.access.access import AbstractAccessDomain
from bastion.domain.access.platform import AccessPlatform


@runtime_checkable
class IAccessLike(Protocol):
    name: str
    platform: AccessPlatform
    tags: dict[str, str]

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> IAccessLike: ...

    @classmethod
    def from_domain(
        cls,
        domain: AbstractAccessDomain,
    ) -> IAccessLike: ...

    def export(self) -> dict[str, Any]: ...
    def describe(self) -> str: ...
