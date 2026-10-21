from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractDomain


class BaseDRAResult(IAbstractDomain):
    """
    Base class for all DRA result models
    model is immutable and cannot be modified after creation

    """

    model_config = ConfigDict(frozen=True)


class DRADatasetResult(BaseDRAResult):
    """
    A dataset mounted in a DRA session
    record dataset specifications under a source

    Attributes:
    ----------
        name (str):
            Dataset name, "<source>.<dataset>", queryable as is in SQL
        description (str):
            Dataset description
        partitions (list[str]):
            Partition keys, exposed as VARCHAR columns

    """

    name: str = Field(
        ...,
        description="Dataset name, '<source>.<dataset>', queryable as is in SQL",
    )
    description: str = Field(
        "",
        description="Dataset description",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition keys, exposed as VARCHAR columns",
    )


class DRAColumnDefinition(BaseDRAResult):
    """
    Definition of a column in a dataset

    Attributes:
    ----------
        name (str):
            Column name
        type (str):
            Column SQL type
        nullable (bool):
            Whether the column is nullable

    """

    name: str = Field(
        ...,
        description="Column name",
    )
    type: str = Field(
        ...,
        description="Column SQL type",
    )
    nullable: bool = Field(
        True,
        description="Whether the column is nullable",
    )


class DRADefinitionResult(BaseDRAResult):
    """
    Live schema of a dataset, taken from the query engine

    Attributes:
    ----------
        dataset (str):
            Dataset name
        columns (list[DRAColumnDefinition]):
            Columns, partition keys included
        partitions (list[str]):
            Partition key names

    """

    dataset: str = Field(
        ...,
        description="Dataset name",
    )
    columns: list[DRAColumnDefinition] = Field(
        ...,
        description="Columns, partition keys included",
    )
    partitions: list[str] = Field(
        default_factory=list,
        description="Partition key names",
    )


class DRAQualityResult(BaseDRAResult):
    """
    Quality records of a dataset

    Attributes:
    ----------
        dataset (str):
            Dataset name
        records (list[dict[str, Any]]):
            Matching records, empty when nothing was stored

    """

    dataset: str = Field(
        ...,
        description="Dataset name",
    )
    records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Matching records, empty when nothing was stored",
    )


class DRADataResult(BaseDRAResult):
    """
    Result of one query

    Attributes:
    ----------
        columns (list[str]):
            Column names
        types (list[str]):
            Column SQL types
        rows (list[list[Any]]):
            Rows, cut at the row or size cap
        truncated (bool):
            Whether rows were dropped by a cap
        truncated_by (Literal["rows", "size"] | None):
            Which cap was hit
        elapsed_ms (float):
            Wall-clock time of the query

    """

    columns: list[str] = Field(
        ...,
        description="Column names",
    )
    types: list[str] = Field(
        ...,
        description="Column SQL types",
    )
    rows: list[list[Any]] = Field(
        ...,
        description="Rows, cut at the row or size cap",
    )
    truncated: bool = Field(
        False,
        description="Whether rows were dropped by a cap",
    )
    truncated_by: Literal["rows", "size"] | None = Field(
        None,
        description="Which cap was hit",
    )
    elapsed_ms: float = Field(
        0.0,
        description="Wall-clock time of the query",
    )
