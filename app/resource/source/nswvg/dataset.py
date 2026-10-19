from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar

import polars as pl
from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.model.metadata.assetfile import AssetfileMetadata
from app.internal.util.dataframe import IDataframe
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source.nswvg.provision import NSWVGProvisionItem, NSWVGProvisionKind


class NSWVGRunMode(StrEnum):
    """
    Run mode of an NSW VG dataset.

    Members:
    -----------
        DELTA:
            Process only the provision items that have no assetfile yet.
        FULL:
            Process every provision item.

    """

    DELTA = "delta"
    FULL = "full"


class NSWVGDataset(BaseDataset):
    """
    Base class for NSW VG PSI datasets, constructed via `NSWVGSource.dataset()`

    One assetfile is written per provision item, items are processed one by one
    so a failure keeps the files already written.

    Attributes:
    ----------
        frn (str):
            Dataset FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.NSWVG
        name (str):
            Dataset name, declared by the subclass
        partitions (list[str]):
            Partition keys of the dataset, declared by the subclass
        filekind (AssetFileKind):
            Asset file kind, fixed to AssetFileKind.PARQUET
        frequency (FrequencyOption):
            Update frequency, default is FrequencyOption.WEEK
        description (str):
            Dataset description, default is ""
        provision_kind (NSWVGProvisionKind):
            Kind of provision items the dataset accepts, declared by the subclass
        provision_path (Path):
            Provision directory of the dataset, created when missing
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
        list_provision_items() -> list[NSWVGProvisionItem]:
            List the provision items of `provision_kind` sorted by key, invalid directories are skipped with a warning.
        discover(mode: NSWVGRunMode = NSWVGRunMode.DELTA) -> list[NSWVGProvisionItem]:
            Delta mode returns the items without assetfile yet, full mode returns every item.
        extract(params: dict | None = None) -> pl.DataFrame:
            Read the provision item named by `params["key"]`.
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Cast the columns to their types, values that fail to parse are set null with a warning.
        write(df: pl.DataFrame) -> list[BaseAssetfile]:
            Split the data by `partitions` and write each part as a parquet assetfile with metadata.
        run(params: dict | None = None) -> list[BaseAssetfile]:
            Only `{"mode": "delta" | "full"}` is accepted, default is delta.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.NSWVG
    filekind: ClassVar[AssetFileKind] = AssetFileKind.PARQUET
    frequency: ClassVar[FrequencyOption] = FrequencyOption.WEEK
    provision_kind: ClassVar[NSWVGProvisionKind]
    # [Inherited] name: ClassVar[str] = ?
    # [Inherited] partitions: ClassVar[str] = ?
    # [Inherited] description: ClassVar[str] = ""

    # Enforced instance variables
    # [Inherited] asset: BaseAsset
    # [Inherited] database: BaseDatabase
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]
    provision_path: Path = Field(
        ...,
        description="[Required] Provision directory of this dataset.",
    )

    @model_validator(mode="after")
    def _derive_provision_path(self) -> NSWVGDataset:
        _path: Path = Path(self.provision_path).expanduser().resolve()
        _path.mkdir(
            parents=True,
            exist_ok=True,
        )
        object.__setattr__(self, "provision_path", _path)
        return self

    def list_provision_items(self) -> list[NSWVGProvisionItem]:
        _provs: list[NSWVGProvisionItem] = []
        for _dir in self.provision_path.iterdir():
            if not _dir.is_dir():
                continue
            try:
                _item = NSWVGProvisionItem(path=_dir)
            except Exception as e:
                self.log_stream.warning(f"Failed to add provision item for '{_dir}': {e}")
                continue
            if _item.kind != self.provision_kind:
                self.log_stream.warning(f"Skip '{_dir.name}': kind '{_item.kind}' is not '{self.provision_kind}'")
                continue
            _provs.append(_item)
        return sorted(_provs, key=lambda _f: _f.key)

    def discover(
        self,
        mode: NSWVGRunMode = NSWVGRunMode.DELTA,
    ) -> list[NSWVGProvisionItem]:
        _provs: list[NSWVGProvisionItem] = self.list_provision_items()
        if mode == NSWVGRunMode.FULL:
            return _provs

        _a_ptns: list[dict[str, str]] = []
        for _a in self.list_assetfiles():
            _a_ptns.append(_a.partitions)

        _delta: list[NSWVGProvisionItem] = []
        for _p in _provs:
            if _p.partitions not in _a_ptns:
                _delta.append(_p)
        return _delta

    def _parse_mode(
        self,
        mode: NSWVGRunMode | str | None = None,
    ) -> NSWVGRunMode:
        if mode is None:
            return NSWVGRunMode.DELTA
        try:
            return NSWVGRunMode(mode.lower() if isinstance(mode, str) else mode)
        except ValueError:
            raise ValueError(f"Unknown run mode '{mode}', expected 'delta' or 'full'.") from None

    def extract(
        self,
        params: dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        _key: str | None = (params or {}).get("key")
        if not _key or Path(_key).name != _key:
            raise ValueError("Param 'key' must be the name of a provision item.")
        _item_path: Path = self.provision_path / _key
        _item = NSWVGProvisionItem(path=_item_path)
        return _item.read()

    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        _res: pl.DataFrame = df.with_columns(
            pl.col("sale_counter").cast(pl.Int32, strict=False),
            pl.col("download_time").str.strptime(pl.Datetime("us"), "%Y%m%d %H:%M", strict=False),
            pl.col("area", "purchase_price", "interest_of_sale").cast(pl.Float64, strict=False),
            pl.col("contract_date", "settlement_date").str.strptime(pl.Date, "%Y%m%d", strict=False),
        )
        for _col in _res.columns:
            _lost: int = _res[_col].null_count() - df[_col].null_count()
            if _lost > 0:
                self.log_stream.warning(f"{_lost} unparsable values of '{_col}' set null")
        return _res

    def write(
        self,
        df: pl.DataFrame,
    ) -> list[BaseAssetfile]:
        if df.is_empty():
            return []

        # Check for missing required partition columns
        _missings: list[str] = []
        for _k in self.partitions:
            if _k not in df.columns:
                _missings.append(_k)
        if _missings:
            raise ValueError(f"Required partition columns not found: {_missings}")

        # Partition the DataFrame by the required partition columns
        _groups: dict[tuple, pl.DataFrame] = df.partition_by(
            self.partitions,
            as_dict=True,
            maintain_order=True,
        )

        # Write each partitioned DataFrame to an assetfile
        _files: list[BaseAssetfile] = []
        for _values, _part in _groups.items():
            _bytes: bytes = IDataframe.to_parquet_bytes(_part)
            _fp: str = IDataframe.to_fingerprint(_bytes)
            _file: BaseAssetfile = self.asset.assetfile(
                name=f"{_fp}.parquet",
                partitions={_k: str(_v) for _k, _v in zip(self.partitions, _values)},
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

    def run(
        self,
        params: dict[str, Any] | None = None,
    ) -> list[BaseAssetfile]:
        _params: dict[str, Any] = params or {}
        _mode: NSWVGRunMode = self._parse_mode(_params.get("mode"))
        _items: list[NSWVGProvisionItem] = self.discover(mode=_mode)
        if not _items:
            self.log_stream.info(f"No items discovered in {_mode} mode")
            return []
        _files: list[BaseAssetfile] = []
        for _item in _items:
            _files.extend(super().run({"key": _item.key}))
        return _files
