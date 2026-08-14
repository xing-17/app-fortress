from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel


class BaseBridgeModel(IBastionModel):
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
