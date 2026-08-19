from __future__ import annotations

from typing import Any

from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset.base import BaseAssetModel


class AssetFactory:
    _registry: dict[str, type[IAssetLike]] = {}

    @classmethod
    def register(
        cls,
        platform: str,
        asset_cls: type[IAssetLike],
    ) -> None:
        cls._registry[platform] = asset_cls

    @classmethod
    def load_from_dict(
        cls,
        data: dict[str, Any],
    ) -> IAssetLike:
        platform = data.get("platform")
        if platform is None:
            raise ValueError("Asset data missing required field: 'platform'")

        asset_cls: type[IAssetLike] | None = cls._registry.get(platform)
        if asset_cls is None:
            raise ValueError(f"No asset class registered for platform: '{platform}'")

        return asset_cls.from_dict(data)

    @classmethod
    def load_from_domain(
        cls,
        domain: BaseAssetModel,
    ) -> IAssetLike:
        platform = getattr(domain, "platform", None)
        if platform is None:
            raise ValueError("Domain object missing required attribute: 'platform'")

        asset_cls: type[IAssetLike] | None = cls._registry.get(platform)
        if asset_cls is None:
            raise ValueError(f"No asset class registered for platform: '{platform}'")

        return asset_cls.from_domain(domain)

    @classmethod
    def resolve(
        cls,
        value: IAssetLike | BaseAssetModel | dict[str, Any] | None,
    ) -> IAssetLike | None:
        if value is None:
            return None
        elif isinstance(value, IAssetLike):
            return value
        elif isinstance(value, BaseAssetModel):
            return cls.load_from_domain(value)
        elif isinstance(value, dict):
            return cls.load_from_dict(value)
        else:
            raise TypeError(f"Invalid asset type: {type(value)}")


def _register_defaults() -> None:

    # Register LocalAsset for the "local" platform
    from bastion.control.asset.local.local import LocalAsset

    AssetFactory.register(
        platform="local",
        asset_cls=LocalAsset,
    )

    # Register S3Asset for the "s3" platform
    from bastion.control.asset.s3.s3 import S3Asset

    AssetFactory.register(
        platform="s3",
        asset_cls=S3Asset,
    )

    # Register OSSAsset for the "oss" platform
    from bastion.control.asset.oss.oss import OSSAsset

    AssetFactory.register(
        platform="oss",
        asset_cls=OSSAsset,
    )


_register_defaults()
