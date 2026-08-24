from __future__ import annotations

from typing import Any

from bastion.control.access.base.protocol import IAccessLike
from bastion.domain.access.access import AbstractAccessDomain


class AccessFactory:
    """
    Factory for creating platform-specific access instances.

    Attributes:
        _registry: Platform-to-class mapping.

    Methods:
        add: Decorator to register access class for platform.
        load: Create access instance from data or domain model.
    """

    _registry: dict[str, type[IAccessLike]] = {}

    @classmethod
    def add(
        cls,
        platform: str,
    ) -> None:
        def decorator(klass: type[IAccessLike]):
            if platform in cls._registry:
                raise ValueError(f"'{platform}' access already registered.")
            cls._registry[platform] = klass
            return klass

        return decorator

    @classmethod
    def load(
        cls,
        data: dict[str, Any] | AbstractAccessDomain,
    ) -> IAccessLike:
        # Determine the platform from the data or domain model
        if isinstance(data, AbstractAccessDomain):
            platform = getattr(data, "platform", None)
        else:
            platform = data.get("platform", None)

        if not platform:
            raise ValueError("Access data missing required field: 'platform'")

        # Look up the registered class for the platform
        klass: type[IAccessLike] | None = cls._registry.get(platform)
        if klass is None:
            raise ValueError(f"No access registered for '{platform}'")

        # Determine whether to load from dict or domain model
        if isinstance(data, AbstractAccessDomain):
            return klass.from_domain(data)
        else:
            return klass.from_dict(data)
