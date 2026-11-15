from __future__ import annotations

import warnings
from typing import Any, ClassVar

import polars as pl
from pydantic import ConfigDict

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.model.definition.desc import ColumnDesc
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe
from app.resource.accessory.retry.retry import Retry
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset


class RBADataset(BaseDataset):
    """
    Base class for RBA datasets, constructed via `RBASource.dataset()`

    Every run pulls the whole statistical table through the `rbadata` package
    and stores it as one `snapshotdate` partition (dated in the source timezone),
    revisions are left to downstream models.

    Attributes:
    ----------
        frn (str):
            Dataset FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.RBA
        name (str):
            Dataset name, declared by the subclass
        partitions (list[str]):
            Partition keys of the dataset, declared by the subclass
        filekind (AssetFileKind):
            Asset file kind, fixed to AssetFileKind.PARQUET
        frequency (FrequencyOption):
            Update frequency, declared by the subclass
        description (str):
            Dataset description, default is ""
        table_no (str):
            RBA statistical table number, e.g. "f1.1", declared by the subclass
        retry (Retry):
            Retry policy of the request, default is 3 retries with exponential backoff
        timezone (str):
            IANA timezone inherited from the source, `snapshotdate` is dated in it, default is "UTC"
        asset (BaseAsset):
            Asset holding the dataset files
        database (BaseDatabase):
            Database holding the dataset metadata
        log_stream (LogStream):
            Log stream shared by the source
        tags (dict[str, str]):
            Dataset tags

    Methods:
    ----------
        extract(params: dict | None = None) -> pl.DataFrame:
            Fetch the whole table, `params` is ignored as the table is always pulled in full.
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Add `snapshotdate`, subclasses may extend it.
        write(df: pl.DataFrame) -> list[BaseAssetfile]:
            Split the data by `partitions` and write each part as a parquet assetfile with metadata.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.RBA
    filekind: ClassVar[AssetFileKind] = AssetFileKind.PARQUET
    # [Inherited] name: ClassVar[str] = ?
    # [Inherited] partitions: ClassVar[list[str]] = ?
    # [Inherited] frequency: ClassVar[FrequencyOption] = ?
    # [Inherited] description: ClassVar[str] = ""
    table_no: ClassVar[str]
    retry: ClassVar[Retry] = Retry(
        max_retries=3,
        interval=5,
        backoff_rate=2.0,
    )
    # Every RBA table is a long-format frame with the same columns
    # so the descriptions are shared
    column_descs: ClassVar[list[ColumnDesc]] = [
        ColumnDesc(
            name="date",
            description="Observation date of the value, the last day of the month or quarter for monthly and quarterly tables.",
        ),
        ColumnDesc(
            name="description",
            description="Series description from the RBA table header, with the measure and its qualifiers separated by semicolons.",
        ),
        ColumnDesc(
            name="frequency",
            description="Frequency label from the RBA table header. It is blank for most tables, use the dataset frequency instead.",
        ),
        ColumnDesc(
            name="series_id",
            description="RBA series identifier, unique within a table, e.g. GCPIAG.",
        ),
        ColumnDesc(
            name="series_type",
            description="Series treatment from the RBA table header, e.g. Original, Seasonally adjusted or Indicative.",
        ),
        ColumnDesc(
            name="snapshotdate",
            description="Date the table was pulled, in the source timezone. It is the partition key, not an RBA field.",
        ),
        ColumnDesc(
            name="source",
            description="Download channel used by the rbadata package, normally csv. It is not an RBA publisher field.",
        ),
        ColumnDesc(
            name="table",
            description="RBA statistical table number in upper case, e.g. F1.1.",
        ),
        ColumnDesc(
            name="units",
            description="Unit of the value of this series, e.g. Per cent, $ million, an index base or a currency code.",
        ),
        ColumnDesc(
            name="value",
            description="Observed value of the series on the date, expressed in the units column. Missing observations are dropped.",
        ),
    ]

    # Enforced instance variables
    # [Inherited] asset: BaseAsset
    # [Inherited] database: BaseDatabase
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]

    def _request(self) -> pl.DataFrame:
        try:
            import rbadata
        except ImportError as e:
            raise RuntimeError("rbadata is not installed; run: pip install 'app-fortress[rba]'") from e

        # rbadata parses dd/mm/YYYY without dayfirst, month-end dates are unambiguous so the result is right
        warnings.filterwarnings(
            "ignore",
            message="Parsing dates in .* format when dayfirst=False",
            category=UserWarning,
        )
        # use_cache=False, the local cache of rbadata would make a run return stale data
        _pdf = rbadata.read_rba(table_no=self.table_no, use_cache=False)
        return pl.from_pandas(_pdf)

    def _fetch(self) -> pl.DataFrame:
        _retry: Retry = self.retry.clone(logstream=self.log_stream)
        for _attempt in _retry.attempts():
            with _attempt:
                return self._request()
        _msg: str = f"RBA request failed after table_no={self.table_no}"
        raise RuntimeError(_msg)

    def extract(
        self,
        params: dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        if params:
            self.log_stream.warning(f"RBA table '{self.table_no}' is always pulled in full, params={params} ignored")
        _df: pl.DataFrame = self._fetch()
        if _df.is_empty():
            _msg: str = f"RBA table '{self.table_no}' returned no records"
            self.log_stream.warning(_msg)
        else:
            _msg: str = f"Fetch '{self.table_no}' row={_df.height} OK"
            self.log_stream.debug(_msg)
        return _df

    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        if df.is_empty():
            return df
        return self._col_add_snapshotdate(df)

    def write(
        self,
        df: pl.DataFrame,
    ) -> list[BaseAssetfile]:
        _keys: list[str] = self.partitions
        if df.is_empty():
            return []

        _missings = [k for k in _keys if k not in df.columns]
        if _missings:
            raise ValueError(f"Required partition columns not found: {_missings}")

        if _keys:
            _groups: dict[tuple, pl.DataFrame] = df.partition_by(
                _keys,
                as_dict=True,
                maintain_order=True,
            )
        else:
            _groups = {(): df}

        # One assetfile per partition, named by content fingerprint
        _files: list[BaseAssetfile] = []
        for _values, _part in _groups.items():
            _bytes: bytes = IDataframe.to_parquet_bytes(_part)
            _fp: str = IDataframe.to_fingerprint(_bytes)
            _ptns: dict[str, str] = {k: str(v) for k, v in zip(_keys, _values)}
            _file: BaseAssetfile = self.asset.assetfile(
                name=f"{_fp}.parquet",
                partitions=_ptns,
            )
            self.write_assetfile(
                assetfile=_file,
                bytes=_bytes,
            )
            _metadata: AssetfileMetadata = self.get_metadata(_part)
            self.write_metadata(
                assetfile=_file,
                metadata=_metadata,
            )
            _files.append(_file)

        self.log_stream.info(f"write {len(_files)} assetfiles OK")
        return _files

    def _col_add_snapshotdate(
        self,
        frame: pl.DataFrame,
    ) -> pl.DataFrame:
        _snapshotdate: str = IClock.current_snapshotdate(timezone=self.timezone)
        return frame.with_columns(pl.lit(_snapshotdate).alias("snapshotdate"))
