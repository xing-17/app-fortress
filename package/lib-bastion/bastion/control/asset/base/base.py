from __future__ import annotations

from typing import Protocol, runtime_checkable

from bastion.domain.asset.base import BaseAssetModel


@runtime_checkable
class IAssetLike(Protocol):
    """
    Protocol defining the interface for asset control layer objects.

    Attributes:
        domain (BaseAssetModel): The domain model containing asset metadata.

    Methods:
        get_location_uri() -> str: Return the URI of the asset's location.

    Example:
        ```python
        from bastion.control.asset import LocalAsset

        asset = LocalAsset(
            name="sales_data",
            kind="parquet",
            path="/data/sales.parquet"
        )
        uri = asset.get_location_uri()  # "/data/sales.parquet"
        ```
    """

    domain: BaseAssetModel

    def get_location_uri(self) -> str:
        """Return the URI of the asset's location."""
        ...
