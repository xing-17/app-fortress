from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from bastion._internal.model import IBastionModel
from bastion.domain.asset.base.base import BaseAssetModel
from bastion.domain.store.base.base import BaseStoreModel


class BaseWorkflowModel(IBastionModel):
    _id_prefix: ClassVar[str] = "workflow"
    _id_length: ClassVar[int] = 12
    name: str = Field(
        ...,
        description="Name of the workflow",
    )
    assets: list[BaseAssetModel] = Field(
        default_factory=list,
        description="List of assets associated with the workflow",
    )
    # TODO: add more when ready
    agents: list[object] = Field(
        default_factory=list,
        description="List of agents associated with the workflow",
    )
    # TODO: add more when ready
    runs: list[object] = Field(
        default_factory=list,
        description="List of runs associated with the workflow",
    )
    store: BaseStoreModel | None = Field(
        None,
        description="Store associated with the workflow",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the workflow",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with the workflow",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the workflow",
    )

    def export(self) -> dict[str, Any]:
        _assets_export = [asset.export() for asset in self.assets]
        _agents_export = [agent.export() for agent in self.agents]
        _runs_export = [run.export() for run in self.runs]
        _store_export = self.store.export() if self.store else None
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "tags": self.tags,
            "assets": _assets_export,
            "agents": _agents_export,
            "runs": _runs_export,
            "store": _store_export,
        }
