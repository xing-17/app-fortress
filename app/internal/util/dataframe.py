from __future__ import annotations

import polars as pl
import polars.datatypes as pldt

from app.internal.abstract.utility import IAbstractUtility


class IDataframe(IAbstractUtility):
    @staticmethod
    def _datatype_namespace() -> dict[str, type]:
        _result: dict[str, type] = {}
        for _name, _obj in vars(pldt).items():
            if isinstance(_obj, type) and issubclass(_obj, pl.DataType):
                _result[_name] = _obj
        return _result

    @staticmethod
    def stringify_column_type(type: pl.DataType) -> str:
        return str(type)

    @staticmethod
    def resolve_column_type(name: str) -> pl.DataType:
        try:
            result = eval(
                name,
                {"__builtins__": {}},
                IDataframe._datatype_namespace(),
            )
        except Exception as e:
            raise ValueError(f"Unknown column type: {name!r}") from e

        if isinstance(result, type) and issubclass(result, pl.DataType):
            return result()
        if isinstance(result, pl.DataType):
            return result
        raise ValueError(f"Not a polars DataType: {name!r}")
