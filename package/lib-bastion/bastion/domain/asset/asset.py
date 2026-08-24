from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from pydantic import Field

from bastion.domain.asset.filesystem import AssetFilesystem
from bastion.domain.asset.objectkind import AssetObjectkind
from bastion.internal.idomain import IDomain


class AbstractAssetDomain(
    IDomain,
    ABC,
):
    """
    Abstract base class for logical data asset objects across platforms.

    Attributes:
        name (str): Name of the asset.
        objectkind (AssetObjectkind): Kind of the asset, default: OBJECT.
        filesystem (AssetFilesystem): File system of the asset, default: LOCAL.
        partitions (list[str]): List of partition keys: default: empty list.
        description (str | None): Optional description of the asset.
        owner (str | None): Optional owner of the asset.
        metadata (dict[str, Any]): Additional metadata associated with the asset.
        tags (dict[str, str]): Tags associated with the asset.

    Methods:
        from_dict(dict data): Create instance from dictionary data.
        export(): Export the underlying domain model to a dictionary.
        describe(): Return a JSON string representation of the domain model.
        clone(**updates): Create a deep copy with updates (inherited).

    """

    _id_enabled: ClassVar[bool] = False
    name: str = Field(
        ...,
        description="Name of the asset",
    )
    objectkind: AssetObjectkind = Field(
        AssetObjectkind.OBJECT,
        description="Kind of the asset",
    )
    filesystem: AssetFilesystem = Field(
        AssetFilesystem.LOCAL,
        description="File system of the asset",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys for the asset",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the asset",
    )
    owner: str | None = Field(
        default=None,
        description="Owner of the asset",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata associated with the asset",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags associated with the asset",
    )
