from __future__ import annotations

import hashlib
import json

import polars as pl
from pydantic import Field, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe


class ColumnDefinition(IAbstractDomain):
    """
    Column-level schema definition for a single column in a dataset.

    Args:
    ---------
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
    ---------
        created_at (float | None):
            The creation timestamp of the dataset definition, in UTC.
        columns (list[ColumnDefinition]):
            The columns of the dataset for this definition.
        fingerprint (str | None):
            The fingerprint of the dataset definition, derived from its columns.

    Methods:
    ---------
        from_frame(cls, df: pl.DataFrame) -> DataframeDefinition:
            Build a DataframeDefinition from a polars DataFrame's columns.

    """

    created_at: float | None = Field(
        default=None,
        description="The creation timestamp of the dataset definition, in UTC.",
    )
    columns: list[ColumnDefinition] = Field(
        default_factory=list,
        description="The columns of the dataset for this definition.",
    )
    fingerprint: str | None = Field(
        default=None,
        description="The fingerprint of the dataset definition, derived from its columns.",
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

    @model_validator(mode="after")
    def _derive_fingerprint(self) -> DataframeDefinition:
        if not self.fingerprint:
            _col_objs: list[ColumnDefinition] = self.columns
            _col_objs = sorted(_col_objs, key=lambda c: c.name)
            _cols: dict[str, str] = {col.name: col.type for col in _col_objs}
            _string: str = json.dumps(
                _cols,
                ensure_ascii=False,
                sort_keys=True,
            )
            _encoded: bytes = _string.encode("utf-8")
            _fp: str = hashlib.sha256(_encoded).hexdigest()
            object.__setattr__(self, "fingerprint", _fp)
        return self

    @classmethod
    def from_frame(
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
