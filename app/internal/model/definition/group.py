from __future__ import annotations

from pydantic import Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.model.definition.dataframe import ColumnDefinition


class DefinitionGroup(IAbstractDomain):
    """
    Partitions of a dataset that share one definition

    Args:
    ----------
        fingerprint (str):
            Fingerprint of the shared definition
        columns (list[ColumnDefinition]):
            Columns of the shared definition
        partitions (list[dict[str, str]]):
            Partitions of the assetfiles carrying this definition

    """

    fingerprint: str = Field(
        ...,
        description="Fingerprint of the shared definition",
    )
    columns: list[ColumnDefinition] = Field(
        default_factory=list,
        description="Columns of the shared definition",
    )
    partitions: list[dict[str, str]] = Field(
        default_factory=list,
        description="Partitions of the assetfiles carrying this definition",
    )
