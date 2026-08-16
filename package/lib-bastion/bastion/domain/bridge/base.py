from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class BaseBridgeModel(IBastionModel):
    """
    Represents the bridge relationship connecting compute resources to data assets.

    Attributes:
        id (str): Unique identifier (inherited from IBastionModel, disabled for bridges).
        name (str): Name of the bridge.
        compute_name (str | None): Compute name associated with the bridge.
        asset_names (list[str]): List of asset names associated with the bridge.
        description (str | None): Optional description of the bridge.
        metadata (dict[str, Any]): Metadata associated with the bridge.
        tags (dict[str, str]): Tags associated with the bridge.

    Methods:
        from_any(value): Convert dict or instance to bridge model (inherited).
        export(): Export the bridge data as a dictionary.
        describe(): Export bridge as JSON string (inherited).
        clone(**updates): Create a deep copy with updates (inherited).
        logic_name: Get logical name of the bridge (inherited property).
        sha256: Get SHA256 hash of the bridge (inherited property).

    Example:
        ```python
        bridge = BaseBridgeModel(
            name="data-bridge",
            compute_name="compute-01",
            asset_names=["asset-01", "asset-02"],
            description="Bridge for data processing",
            metadata={"priority": "high"},
            tags={"env": "prod"}
        )
        data = bridge.export()
        ```
    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the bridge",
    )
    compute_name: str | None = Field(
        default=None,
        description="Compute name associated with the bridge",
    )
    asset_names: list[str] = Field(
        default_factory=list,
        description="List of asset names associated with the bridge",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the bridge",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with the bridge",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the bridge",
    )

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "compute_name": self.compute_name,
            "asset_names": self.asset_names,
            "description": self.description,
            "metadata": self.metadata,
            "tags": self.tags,
        }
