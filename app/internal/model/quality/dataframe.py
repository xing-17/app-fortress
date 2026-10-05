from __future__ import annotations

import polars as pl
from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe
from app.internal.util.id import IID


class ColumnQuality(IAbstractDomain):
    """
    Column-level data quality metrics for a single column in a dataset.

    Args:
        name (str): The name of the column in the dataset.
        type (str): The data type of the column in the dataset.
        complete_count (int): The complete count of the column.
        complete_rate (float): The complete rate of the column, represented as a float between 0 and 1.
        null_count (int): The null count of the column.
        null_rate (float): The null rate of the column, represented as a float between 0 and 1.
        unique_count (int): The unique count of the column.
        unique_rate (float): The unique rate of the column, represented as a float between 0 and 1.
        duplicate_count (int): The duplicate count of the column.
        duplicate_rate (float): The duplicate rate of the column, represented as a float between 0 and 1.

    """

    name: str = Field(
        ...,
        description="The name of the column in the dataset.",
    )
    type: str = Field(
        ...,
        description="The data type of the column in the dataset.",
    )
    complete_count: int = Field(
        default=0,
        description="The complete count of the column.",
        ge=0,
    )
    complete_rate: float = Field(
        default=0.0,
        description="The complete rate of the column, represented as a float between 0 and 1.",
        ge=0.0,
        le=1.0,
    )
    null_count: int = Field(
        default=0,
        description="The null count of the column.",
        ge=0,
    )
    null_rate: float = Field(
        default=0.0,
        description="The null rate of the column, represented as a float between 0 and 1.",
        ge=0.0,
        le=1.0,
    )
    unique_count: int = Field(
        default=0,
        description="The unique count of the column.",
        ge=0,
    )
    unique_rate: float = Field(
        default=0.0,
        description="The unique rate of the column, represented as a float between 0 and 1.",
        ge=0.0,
        le=1.0,
    )
    duplicate_count: int = Field(
        default=0,
        description="The duplicate count of the column.",
        ge=0,
    )
    duplicate_rate: float = Field(
        default=0.0,
        description="The duplicate rate of the column, represented as a float between 0 and 1.",
        ge=0.0,
        le=1.0,
    )


class DataframeQuality(IAbstractDomain):
    """
    Dataframe-level data quality report aggregating column-level quality metrics.

    Args:
        id (str): The unique identifier for the dataset quality record.
        width (int): The number of columns in the dataset.
        height (int): The number of rows in the dataset.
        is_empty (bool): Indicates whether the dataset is empty (i.e., has no rows or columns).
        created_at (float | None): The creation timestamp of the dataset quality record, in UTC.
        complete_rows (int): The number of complete rows in the dataset.
        duplicate_rows (int): The number of duplicate rows in the dataset.
        columns (list[ColumnQuality]): The quality metrics of the columns in the dataset.

    Methods:
        from_df(cls, df: pl.DataFrame) -> DataframeQuality:
            Compute a DataframeQuality report from a polars DataFrame.

    """

    id: str = Field(
        default_factory=lambda: IID.generate_id(length=16, prefix="quality"),
        description="The unique identifier for the dataset quality record.",
    )
    width: int = Field(
        default=0,
        description="The number of columns in the dataset.",
        ge=0,
    )
    height: int = Field(
        default=0,
        description="The number of rows in the dataset.",
        ge=0,
    )
    is_empty: bool = Field(
        default=False,
        description="Indicates whether the dataset is empty (i.e., has no rows or columns).",
    )
    created_at: float | None = Field(
        default=None,
        description="The creation timestamp of the dataset quality record, in UTC.",
    )
    complete_rows: int = Field(
        default=0,
        description="The number of complete rows in the dataset.",
        ge=0,
    )
    duplicate_rows: int = Field(
        default=0,
        description="The number of duplicate rows in the dataset.",
        ge=0,
    )
    columns: list[ColumnQuality] = Field(
        default_factory=list,
        description="The quality metrics of the columns in the dataset.",
    )

    @model_validator(mode="after")
    def _derive_is_empty(self) -> DataframeQuality:
        if self.height == 0 or self.width == 0:
            object.__setattr__(self, "is_empty", True)
        else:
            object.__setattr__(self, "is_empty", False)
        return self

    @model_validator(mode="after")
    def _derive_created_at(self) -> DataframeQuality:
        if not self.created_at:
            _current: float = IClock.current_timestamp(timezone="UTC")
            object.__setattr__(self, "created_at", _current)
        return self

    @model_validator(mode="after")
    def _derive_columns(self) -> DataframeQuality:
        _sorted = sorted(self.columns, key=lambda col: col.name)
        object.__setattr__(self, "columns", _sorted)
        return self

    @classmethod
    def from_df(
        cls,
        df: pl.DataFrame,
    ) -> "DataframeQuality":
        _width = len(df.columns)
        _height = df.height
        _columns: list[ColumnQuality] = []

        if df.is_empty():
            _complete_rows = 0
            _duplicate_rows = 0
            for _col in df.columns:
                _col_name: str = _col
                _col_series = df[_col]
                _col_type = IDataframe.stringify_column_type(_col_series.dtype)
                _col_quality = ColumnQuality(
                    name=_col_name,
                    type=_col_type,
                )
                _columns.append(_col_quality)
        else:
            _complete_rows = df.select(pl.all_horizontal(pl.all().is_not_null()).sum()).item()
            _duplicate_rows = int(df.is_duplicated().sum())
            for _col in df.columns:
                _col_name: str = _col
                _col_series = df[_col]
                _col_type = IDataframe.stringify_column_type(_col_series.dtype)
                _complete_count = _col_series.drop_nulls().len()
                _complete_rate = (_complete_count / _height) if _height > 0 else 0.0
                _null_count = _col_series.null_count()
                _null_rate = (_null_count / _height) if _height > 0 else 0.0
                _unique_count = _col_series.n_unique()
                _unique_rate = (_unique_count / _height) if _height > 0 else 0.0
                _duplicate_count = _col_series.len() - _unique_count
                _duplicate_rate = (_duplicate_count / _height) if _height > 0 else 0.0
                _col_quality = ColumnQuality(
                    name=_col_name,
                    type=_col_type,
                    complete_count=_complete_count,
                    complete_rate=_complete_rate,
                    null_count=_null_count,
                    null_rate=_null_rate,
                    unique_count=_unique_count,
                    unique_rate=_unique_rate,
                    duplicate_count=_duplicate_count,
                    duplicate_rate=_duplicate_rate,
                )
                _columns.append(_col_quality)

        return cls(
            width=_width,
            height=_height,
            complete_rows=_complete_rows,
            duplicate_rows=_duplicate_rows,
            columns=_columns,
        )
