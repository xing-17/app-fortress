from __future__ import annotations

from abc import abstractmethod
from typing import Callable, ClassVar

import polars as pl
from pydantic import Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe
from app.resource.accessory.coolant.coolant import Coolant
from app.resource.accessory.jitter.jitter import Jitter
from app.resource.accessory.paginate.paginate import Paginate
from app.resource.accessory.retry.retry import Retry
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source.tushare.session import TushareSession


class TushareDataset(BaseDataset):
    """
    Base class for Tushare datasets, constructed via `TushareSource.dataset()`

    Attributes:
    ----------
        frn (str):
            Dataset FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.TUSHARE
        name (str):
            Dataset name, declared by the subclass
        partitions (list[str]):
            Partition keys of the dataset, default is []
        filekind (AssetFileKind):
            Asset file kind, fixed to AssetFileKind.PARQUET
        frequency (FrequencyOption):
            Update frequency, default is FrequencyOption.DAY
        description (str):
            Dataset description, default is ""
        method (str):
            Tushare API method name, declared by the subclass
        paginate (Paginate):
            Pagination configuration, declared by the subclass
        jitter (Jitter):
            Random sleep between pages, default is 0 ~ 0.2 seconds
        coolant (Coolant):
            Fixed sleep between pages, default is 0 seconds
        retry (Retry):
            Retry policy of a single page request, default is 3 retries
        session (TushareSession):
            Tushare session for API calls
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
        call(method: str, params: dict) -> pl.DataFrame:
            Call a Tushare API method page by page with retry, and concatenate the pages.
        extract(params: dict | None = None) -> pl.DataFrame:
            Extract raw data by calling the declared `method`.
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Transform the extracted data, declared by the subclass.
        write(df: pl.DataFrame) -> list[BaseAssetfile]:
            Split the data by `partitions` and write each part as a parquet assetfile with metadata.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.TUSHARE
    filekind: ClassVar[AssetFileKind] = AssetFileKind.PARQUET
    frequency: ClassVar[FrequencyOption] = FrequencyOption.DAY
    # [Inherited] name: ClassVar[str] = ?
    # [Inherited] partitions: ClassVar[str] = ?
    # [Inherited] description: ClassVar[str] = ""
    method: ClassVar[str]
    paginate: ClassVar[Paginate]  # NO default pagination configuration
    jitter: ClassVar[Jitter] = Jitter(  # Default jitter configuration
        min_seconds=0,
        max_seconds=0.2,
    )
    coolant: ClassVar[Coolant] = Coolant(  # Default coolant configuration
        interval=0,
    )
    retry: ClassVar[Retry] = Retry(  # Default retry configuration
        max_retries=3,
        interval=1,
        backoff_rate=1.0,
    )

    # Enforced private class variables
    # [Inherited] _table_qual_name: str
    # [Inherited] _table_qual_ttl_hours: int | None
    # [Inherited] _table_def_name: str
    # [Inherited] _table_def_ttl_hours: int | None
    # [Inherited] _table_files_name: str
    # [Inherited] _table_files_ttl_hours: int | None

    # Enforced instance variables
    session: TushareSession = Field(
        ...,
        description="Tushare session for API calls.",
    )
    # [Inherited] asset: BaseAsset
    # [Inherited] database: BaseDatabase
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]
    # [Inherited] _table_def: BaseTable
    # [Inherited] _table_qual: BaseTable
    # [Inherited] _table_files: BaseTable

    def _check_session(self) -> bool:
        if not self.session:
            return False
        if not self.session.api:
            return False
        return True

    def _fetch_page(
        self,
        callable: Callable,
        params: dict,
        retry: Retry,
    ) -> pl.DataFrame:
        for _attempt in retry.attempts():
            with _attempt:
                return pl.from_pandas(callable(**params))
        raise RuntimeError(f"Tushare page fetch failed, params={params}")

    def call(
        self,
        method: str,
        params: dict,
    ) -> pl.DataFrame:
        # Ensure that the session is available
        if not self._check_session():
            raise ValueError("Tushare session is not ready.")

        # Secure API method access
        _callable = getattr(self.session.api, method, None)
        if not _callable or not callable(_callable):
            raise ValueError(f"Tushare API method '{method}' not found.")

        # Paginate through the API results
        _paginate: Paginate = self.paginate.clone()
        _retry: Retry = self.retry.clone()
        _frames: list[pl.DataFrame] = []
        for _page in _paginate.pages():
            _params = params.copy() if params else {}
            _params["limit"] = _page.size
            _params["offset"] = _page.offset
            _frame = self._fetch_page(_callable, _params, _retry)
            if _frame.is_empty():
                break
            _frames.append(_frame)
            self.log_stream.debug(f"Invoke '{method}' page={_page.number} row={_frame.height} OK")

            # Last page must < size
            if _frame.height < _page.size:
                break
            if self.coolant:
                self.coolant.run()
            if self.jitter:
                self.jitter.run()

        if _frames:
            return pl.concat(
                _frames,
                how="vertical_relaxed",
                rechunk=False,
            )
        else:
            return pl.DataFrame()

    def extract(
        self,
        params: dict | None = None,
    ) -> pl.DataFrame:
        return self.call(
            method=self.method,
            params=params,
        )

    @abstractmethod
    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame: ...

    def write(
        self,
        df: pl.DataFrame,
    ) -> list[BaseAssetfile]:
        # Partition must be predefined in the dataset's partitions list
        _keys: list[str] = self.partitions
        if df.is_empty():
            return []

        # Raise ValueError if partition columns are missing
        _missings = [k for k in _keys if k not in df.columns]
        if _missings:
            raise ValueError(f"Required partition columns not found: {_missings}")

        # Partition the DataFrame by the specified keys
        if _keys:
            _groups: dict[tuple, pl.DataFrame] = df.partition_by(
                _keys,
                as_dict=True,
                maintain_order=True,
            )
        else:
            _groups = {(): df}

        # Iterate over each group into SEPARATE assetfile
        _files: list[BaseAssetfile] = []
        _metas: list[AssetfileMetadata] = []
        for _values, _part in _groups.items():
            _bytes: bytes = IDataframe.to_parquet_bytes(_part)
            _fp: str = IDataframe.to_fingerprint(_bytes)
            _ptns: dict[str, str] = {k: str(v) for k, v in zip(_keys, _values)}
            _filename: str = f"{_fp}.parquet"

            # Create a new assetfile for the current partition
            _file: BaseAssetfile = self.asset.assetfile(
                name=_filename,
                partitions=_ptns,
            )
            self.write_assetfile(
                assetfile=_file,
                bytes=_bytes,
            )
            _files.append(_file)

            # Write metadata for the current assetfile
            _metadata: AssetfileMetadata = self.get_metadata(_part)
            self.write_metadata(
                assetfile=_file,
                metadata=_metadata,
            )
            _metas.append(_metadata)

        self.log_stream.info(f"write {len(_files)} assetfiles OK")
        self.log_stream.info(f"write {len(_metas)} metadatas OK")
        return _files

    # ---------- Column manipulation helpers ----------

    def _col_add_snapshotdate(
        self,
        frame: pl.DataFrame,
    ) -> pl.DataFrame:
        # A column-less empty frame would otherwise broadcast the literal into one bogus row
        if frame.is_empty():
            return frame
        _snapshotdate: str = IClock.current_snapshotdate(timezone="UTC")
        return frame.with_columns(pl.lit(_snapshotdate).alias("snapshotdate"))

    def _col_format_date_value(
        self,
        df: pl.DataFrame,
        cols: list[str],
    ) -> pl.DataFrame:
        for col in cols:
            if col in df.columns:
                df = df.with_columns(pl.col(col).str.strptime(pl.Date, format="%Y%m%d"))
        return df

    def _col_ensure_float_columns(
        self,
        df: pl.DataFrame,
        cols: list[str],
    ) -> pl.DataFrame:
        for col in cols:
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(pl.Float64))
        return df

    def _col_ensure_bool_columns(
        self,
        df: pl.DataFrame,
        cols: list[str],
    ) -> pl.DataFrame:
        for col in cols:
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(pl.Boolean))
        return df
