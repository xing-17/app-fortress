from __future__ import annotations

import polars as pl
from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe
from app.internal.util.id import IID


class ColumnDefinition(IAbstractDomain):
    """
    Column-level schema definition for a single column in a dataset.

    Args:
        name (str): The name of the column in the dataset.
        type (str): The data type of the column in the dataset.

    """

    name: str = Field(
        ...,
        description="The name of the column in the dataset.",
    )
    type: str = Field(
        ...,
        description="The data type of the column in the dataset.",
    )


class DataframeDefinition(IAbstractDomain):
    """
    Dataframe-level schema definition aggregating column-level definitions.

    Args:
        id (str): The unique identifier for the dataset definition.
        created_at (float | None): The creation timestamp of the dataset definition, in UTC.
        columns (list[ColumnDefinition]): The columns of the dataset for this definition.

    Methods:
        from_df(cls, df: pl.DataFrame) -> DataframeDefinition:
            Build a DataframeDefinition from a polars DataFrame's columns.

    """

    id: str = Field(
        default_factory=lambda: IID.generate_id(length=16, prefix="def"),
        description="The unique identifier for the dataset definition.",
    )
    created_at: float | None = Field(
        default=None,
        description="The creation timestamp of the dataset definition, in UTC.",
    )
    columns: list[ColumnDefinition] = Field(
        default_factory=list,
        description="The columns of the dataset for this definition.",
    )

    @model_validator(mode="after")
    def _derive_created_at(self) -> DataframeDefinition:
        if not self.created_at:
            _current: float = IClock.current_timestamp(timezone="UTC")
            object.__setattr__(self, "created_at", _current)
        return self

    @model_validator(mode="after")
    def _derive_columns(self) -> DataframeDefinition:
        _sorted = sorted(self.columns, key=lambda col: col.name)
        object.__setattr__(self, "columns", _sorted)
        return self

    @classmethod
    def from_df(
        cls,
        df: pl.DataFrame,
    ) -> DataframeDefinition:
        _columns: list[ColumnDefinition] = []
        for _col in df.columns:
            _col_name: str = _col
            _col_type: pl.DataType = df[_col].dtype
            _col_def: ColumnDefinition = ColumnDefinition(
                name=_col_name,
                type=IDataframe.stringify_column_type(_col_type),
            )
            _columns.append(_col_def)
        return cls(columns=_columns)
