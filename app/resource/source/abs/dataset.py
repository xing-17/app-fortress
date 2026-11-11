from __future__ import annotations

import io
from typing import Any, ClassVar

import polars as pl
import requests
from pydantic import ConfigDict, Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.util.clock import IClock
from app.internal.util.dataframe import IDataframe
from app.resource._client.web.client import WebClient
from app.resource.accessory.jitter.jitter import Jitter
from app.resource.accessory.retry.retry import Retry
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset


class ABSDataset(BaseDataset):
    """
    Base class for ABS datasets, constructed via `ABSSource.dataset()`

    Every run pulls the whole dataflow through the ABS SDMX REST API as CSV
    and stores it as one `snapshotdate` partition (dated in the source timezone),
    revisions are left to downstream models.

    Attributes:
    ----------
        frn (str):
            Dataset FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.ABS
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
        dataflow_id (str):
            ABS dataflow id, e.g. "JV", declared by the subclass
        agency_id (str):
            SDMX agency id, default is "ABS"
        version (str | None):
            Dataflow version, e.g. "2.0.0", default is None (the latest version)
        key (str):
            SDMX series key, default is "all"
        base_url (str):
            ABS SDMX REST API root
        jitter (Jitter):
            Random sleep before the request, default is 0 ~ 0.2 seconds
        retry (Retry):
            Retry policy of the request, default is 5 retries with exponential backoff
        client (WebClient):
            HTTP client shared by the source
        timeout_seconds (float):
            Timeout of a single request, shared by the source
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
            Fetch the dataflow as CSV, `params` are passed as query string (e.g. startPeriod).
            A "NoRecordsFound" reply is an empty frame, any other error is raised.
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Cast `OBS_VALUE` to float and add `snapshotdate`, subclasses may extend it.
        write(df: pl.DataFrame) -> list[BaseAssetfile]:
            Split the data by `partitions` and write each part as a parquet assetfile with metadata.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.ABS
    filekind: ClassVar[AssetFileKind] = AssetFileKind.PARQUET
    # [Inherited] name: ClassVar[str] = ?
    # [Inherited] partitions: ClassVar[list[str]] = ?
    # [Inherited] frequency: ClassVar[FrequencyOption] = ?
    # [Inherited] description: ClassVar[str] = ""
    dataflow_id: ClassVar[str]
    agency_id: ClassVar[str] = "ABS"
    version: ClassVar[str | None] = None
    key: ClassVar[str] = "all"
    base_url: ClassVar[str] = "https://data.api.abs.gov.au/rest"
    jitter: ClassVar[Jitter] = Jitter(
        min_seconds=0.5,
        max_seconds=1.5,
    )
    # The API is flaky, 4xx other than 429 never recovers by retrying
    retry: ClassVar[Retry] = Retry(
        max_retries=5,
        interval=5,
        backoff_rate=2.0,
        critical_error_exprs=[
            "400 Client Error*",
            "401 Client Error*",
            "403 Client Error*",
            "404 Client Error*",
            "422 Client Error*",
        ],
    )

    # Enforced private class variables
    _no_records_body: ClassVar[str] = "NoRecordsFound"

    # Enforced instance variables
    # [Inherited] asset: BaseAsset
    # [Inherited] database: BaseDatabase
    # [Inherited] log_stream: LogStream
    # [Inherited] max_threads: int
    # [Inherited] timezone: str
    # [Inherited] tags: dict[str, str]
    client: WebClient = Field(
        ...,
        description="[Required] HTTP client, shared by source.",
        exclude=True,
    )
    timeout_seconds: float = Field(
        default=60,
        description="[Optional] Timeout of a single request in seconds.",
        gt=0,
    )

    def _data_url(self) -> str:
        if self.version is None:
            _ref: str = self.dataflow_id
        else:
            _ref: str = f"{self.agency_id},{self.dataflow_id},{self.version}"
        return f"{self.base_url}/data/{_ref}/{self.key}"

    def _request(
        self,
        params: dict[str, Any],
    ) -> pl.DataFrame:
        try:
            _response: requests.Response = self.client.request(
                "GET",
                self._data_url(),
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.HTTPError as e:
            # ABS answers 404 for an empty result too, only its body tells it from an unknown dataflow
            _failed: requests.Response | None = e.response
            if _failed is not None and _failed.status_code == 404 and _failed.text.strip() == self._no_records_body:
                return pl.DataFrame()
            raise
        if not _response.content.strip():
            return pl.DataFrame()

        # Everything is read as string
        # `transform` owns the typing
        return pl.read_csv(
            io.BytesIO(_response.content),
            infer_schema=False,
        )

    def _fetch(
        self,
        params: dict[str, Any],
    ) -> pl.DataFrame:
        _retry: Retry = self.retry.clone(logstream=self.log_stream)
        for _attempt in _retry.attempts():
            with _attempt:
                return self._request(params)
        _msg: str = f"ABS request failed after dataflow={self.dataflow_id}, params={params}"
        raise RuntimeError(_msg)

    def extract(
        self,
        params: dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        _params: dict[str, Any] = {**(params or {}), "format": "csv"}
        if self.jitter:
            self.jitter.run()
        _df: pl.DataFrame = self._fetch(_params)
        if _df.is_empty():
            _msg: str = f"ABS dataflow '{self.dataflow_id}' returned no records, params={params}"
            self.log_stream.warning(_msg)
        else:
            _msg: str = f"Fetch '{self.dataflow_id}' row={_df.height} OK"
            self.log_stream.debug(_msg)
        return _df

    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        if df.is_empty():
            return df
        _res: pl.DataFrame = df
        if "OBS_VALUE" in df.columns:
            _res = df.with_columns(pl.col("OBS_VALUE").cast(pl.Float64, strict=False))
            _lost: int = _res["OBS_VALUE"].null_count() - df["OBS_VALUE"].null_count()
            if _lost > 0:
                _msg: str = f"{_lost} unparsable values of 'OBS_VALUE' set null"
                self.log_stream.warning(_msg)
        return self._col_add_snapshotdate(_res)

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
