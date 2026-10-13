from __future__ import annotations

import hashlib
from io import BytesIO

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
        _namespace = IDataframe._datatype_namespace()
        _obj = _namespace.get(name)
        if _obj is None:
            raise ValueError(f"Unknown column type: {name!r}")
        if isinstance(_obj, type) and issubclass(_obj, pl.DataType):
            return _obj()
        if isinstance(_obj, pl.DataType):
            return _obj
        raise ValueError(f"Not a polars DataType: {name!r}")

    @staticmethod
    def to_parquet_bytes(
        df: pl.DataFrame,
        compression: str = "zstd",
        metadata: dict[str, str] | None = None,
    ) -> tuple[bytes, str]:
        with BytesIO() as buf:
            df.write_parquet(
                buf,
                compression=compression,
                use_pyarrow=False,
                metadata=metadata,
            )
            _result: bytes = buf.getvalue()
            _dna = hashlib.sha256(_result).hexdigest()[:32]
            return _result, _dna
