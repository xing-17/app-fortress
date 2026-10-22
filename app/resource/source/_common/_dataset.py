from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import polars as pl
from pydantic import Field

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.logstream import LogStream
from app.internal.model.definition.dataframe import DataframeDefinition
from app.internal.model.definition.group import DefinitionGroup
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.model.quality import DataframeQuality
from app.internal.util.frn import IFrn
from app.internal.util.stopwatch import IStopwatch
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._base import GovernedSourceResource
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._table import BaseTable


class BaseDataset(
    GovernedSourceResource,
    ABC,
):
    """
    Base class for datasets in the source system, constructed via `BaseSource.dataset()`

    Attributes:
    ----------
        frn (str):
            Dataset FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, declared by the subclass
        name (str):
            Dataset name, declared by the subclass
        partitions (list[str]):
            Partition keys of the dataset, default is []
        filekind (AssetFileKind):
            Asset file kind, default is AssetFileKind.OBJECT
        frequency (FrequencyOption):
            Update frequency, declared by the subclass
        description (str):
            Dataset description, default is ""
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
        extract(params: dict[str, Any] | None = None) -> pl.DataFrame:
            Extract raw data from the provider.
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Transform the extracted data.
        write(df: pl.DataFrame) -> list[BaseAssetfile]:
            Write the transformed data into assetfiles.
        run(params: dict[str, Any] | None = None) -> list[BaseAssetfile]:
            Run extract, transform and write in order, logging metrics and duration.
        write_assetfile(assetfile: BaseAssetfile, bytes: bytes) -> BaseAssetfile:
            Write raw bytes into an assetfile.
        read_assetfile(assetfile: BaseAssetfile) -> bytes:
            Read raw bytes from an assetfile.
        list_assetfiles(since=None, until=None) -> list[BaseAssetfile]:
            List assetfiles of the dataset asset.
        get_metadata_table(name: str) -> BaseTable:
            Get the metadata table of the given name from the dataset database.
        get_metadata(df: pl.DataFrame) -> AssetfileMetadata:
            Build assetfile metadata from a dataframe.
        write_metadata(assetfile: BaseAssetfile, metadata: AssetfileMetadata) -> BaseTable:
            Write the metadata of an assetfile into its metadata table.
        read_metadata(assetfile: BaseAssetfile) -> AssetfileMetadata:
            Read the metadata of an assetfile from its metadata table.
        list_metadatas(since=None, until=None) -> list[AssetfileMetadata]:
            Read the metadata of all assetfiles matching the filter.
        list_qualities(since=None, until=None) -> list[tuple[BaseAssetfile, DataframeQuality]]:
            Quality of each assetfile matching the filter, assetfiles without metadata are skipped.
        list_definitions(since=None, until=None) -> list[DefinitionGroup]:
            Definitions of the assetfiles matching the filter, grouped by fingerprint
            with the partitions that carry each definition.
        export() -> dict[str, Any]:
            Export the dataset as a dictionary.

    """

    # --------------------------------------------------
    # Class variables section
    # --------------------------------------------------

    # ---------- Enforced PUBLIC class variables ----------
    provider: ClassVar[SourceProvider]
    name: ClassVar[str]
    partitions: ClassVar[list[str]] = []
    filekind: ClassVar[AssetFileKind] = AssetFileKind.OBJECT
    frequency: ClassVar[FrequencyOption]
    description: ClassVar[str] = ""

    # ---------- Enforced PRIVATE class variables ----------
    _metadata_key: ClassVar[str] = "__METADATA__"

    # --------------------------------------------------
    # Instance variables section
    # --------------------------------------------------

    # ---------- Enforced PUBLIC instance variables ----------
    #
    # Subclass is not expected to define these instance variables
    #
    # [Inherited] tags: dict[str, str]
    asset: BaseAsset = Field(
        ...,
        description="[Required] Dataset Asset, derived from vault",
    )
    database: BaseDatabase = Field(
        ...,
        description="[Required] Dataset Database for metadata, derived from store",
    )
    log_stream: LogStream = Field(
        ...,
        description="[Required] Dataset Log Stream, shared by source",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "source",
                f"provider={self.provider}",
                "dataset",
                f"name={self.name}",
            ]
        )

    # --------------------------------------------------
    # ETL Ops section
    # --------------------------------------------------
    # Abstract methods for ETL operations
    # Subclasses must implement these methods
    @abstractmethod
    def extract(
        self,
        params: dict[str, Any] | None = None,
    ) -> pl.DataFrame: ...

    @abstractmethod
    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame: ...

    @abstractmethod
    def write(
        self,
        df: pl.DataFrame,
    ) -> list[BaseAssetfile]: ...

    def run(
        self,
        params: dict[str, Any] | None = None,
    ) -> list[BaseAssetfile]:
        IStopwatch.tick()
        try:
            _df: pl.DataFrame = self.extract(params=params)
            _df: pl.DataFrame = self.transform(df=_df)
            _files: list[BaseAssetfile] = self.write(df=_df)
            self.log_stream.info(
                msg=f"Dataset {self.name} run OK",
                metadata={"params": params},
                metrics={
                    "assetfiles": len(_files),
                    "height": _df.height,
                    "width": _df.width,
                },
                tags={"step": "run"},
            )
        except Exception as e:
            self.log_stream.error(msg=f"Dataset {self.name} run failed: {e}", tags={"step": "run"})
            raise
        finally:
            _duration: float = IStopwatch.tock()
        self.log_stream.info(msg=f"Dataset {self.name} run completed in {_duration:.2f}s", tags={"step": "run"})
        return _files

    # --------------------------------------------------
    # Data management Ops section
    # --------------------------------------------------

    def write_assetfile(
        self,
        assetfile: BaseAssetfile,
        bytes: bytes,
    ) -> BaseAssetfile:
        assetfile.write_bytes(data=bytes)
        return assetfile

    def read_assetfile(
        self,
        assetfile: BaseAssetfile,
    ) -> bytes:
        return assetfile.read_bytes()

    def list_assetfiles(
        self,
        since=None,
        until=None,
    ) -> list[BaseAssetfile]:
        return self.asset.list_assetfiles(
            since=since,
            until=until,
        )

    # --------------------------------------------------
    # Metadata management Ops section
    # --------------------------------------------------

    def get_metadata_table(
        self,
        name: str,
    ) -> BaseTable:
        return self.database.table(
            name=name,
            ttl_hours=None,
        )

    def get_metadata(
        self,
        df: pl.DataFrame,
    ) -> AssetfileMetadata:
        return AssetfileMetadata.from_frame(df=df)

    def write_metadata(
        self,
        assetfile: BaseAssetfile,
        metadata: AssetfileMetadata,
    ) -> BaseTable:
        _name: str = assetfile.name
        _record: dict[str, dict] = metadata.export()
        _table: BaseTable = self.get_metadata_table(name=_name)
        _table.write(
            key=self._metadata_key,
            data=_record,
            strict=True,
        )
        return _table

    def read_metadata(
        self,
        assetfile: BaseAssetfile,
    ) -> AssetfileMetadata | None:
        _name: str = assetfile.name
        _table: BaseTable = self.get_metadata_table(name=_name)
        _record: dict[str, dict] = _table.read(
            key=self._metadata_key,
            strict=True,
        )
        if _record is None:
            return None
        return AssetfileMetadata.from_dict(_record)

    def list_metadatas(
        self,
        since=None,
        until=None,
    ) -> list[AssetfileMetadata]:
        _files: list[BaseAssetfile] = self.list_assetfiles(
            since=since,
            until=until,
        )
        _res: list[AssetfileMetadata] = []
        for _file in _files:
            _metadata: AssetfileMetadata | None = self.read_metadata(_file)
            if _metadata is None:
                continue
            _res.append(_metadata)
        return _res

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = self.model_dump(
            exclude={
                "log_stream",
                "asset",
                "database",
            },
            mode="json",
            round_trip=True,
        )
        # ClassVars are not part of model_dump, so add the identity explicitly
        _res["frn"] = self.frn
        _res["provider"] = str(self.provider)
        _res["name"] = self.name
        _res["description"] = self.description
        _res["frequency"] = str(self.frequency)
        _res["filekind"] = str(self.filekind)
        _res["partitions"] = list(self.partitions)
        _res["asset"] = self.asset.export()
        _res["database"] = self.database.export()
        return _res
