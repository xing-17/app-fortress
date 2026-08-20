from __future__ import annotations

from typing import Any

from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset import BaseAssetModel


class AssetFactory:
    """
    Factory for creating platform-specific asset instances.

    Attributes:
        _registry: Platform-to-class mapping.

    Methods:
        register: Decorator to register asset class for platform.
        load: Create asset instance from data or domain model.
    """

    _registry: dict[str, type[IAssetLike]] = {}

    @classmethod
    def register(
        cls,
        platform: str,
    ) -> None:
        def decorator(klass: type[IAssetLike]):
            if platform in cls._registry:
                raise ValueError(f"'{platform}' asset already registered.")
            cls._registry[platform] = klass
            return klass

        return decorator

    @classmethod
    def load(
        cls,
        data: dict[str, Any] | BaseAssetModel,
    ) -> IAssetLike:
        # Determine the platform from the data or domain model
        if isinstance(data, BaseAssetModel):
            platform = getattr(data, "platform", None)
        else:
            platform = data.get("platform", None)

        if not platform:
            raise ValueError("Asset data missing required field: 'platform'")

        # Look up the registered class for the platform
        klass: type[IAssetLike] | None = cls._registry.get(platform)
        if klass is None:
            raise ValueError(f"No asset registered for platform '{platform}'")

        # Determine whether to load from dict or domain model
        if isinstance(data, BaseAssetModel):
            return klass.from_domain(data)
        else:
            return klass.from_dict(data)
