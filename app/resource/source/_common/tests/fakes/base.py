from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import SourceFetchType, SourceProvider, SourceProviderType
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source._common._source import BaseSource

_DATASETS_PKG = "app.resource.source._common.tests.fakes"


class FakeDataset(BaseDataset):
    provider: ClassVar[SourceProvider] = SourceProvider.TUSHARE
    frequency: ClassVar[FrequencyOption] = FrequencyOption.DAY
    filekind: ClassVar[AssetFileKind] = AssetFileKind.PARQUET

    def extract(self, params: dict[str, Any] | None = None) -> pl.DataFrame:
        return pl.DataFrame({"a": [1, 2, 3]})

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns((pl.col("a") * 2).alias("b"))

    def write(self, df: pl.DataFrame) -> list[BaseAssetfile]:
        _file = self.asset.assetfile("data.parquet")
        self.write_assetfile(_file, b"payload")
        return [_file]


class FakeSource(BaseSource):
    provider: ClassVar[SourceProvider] = SourceProvider.TUSHARE
    type: ClassVar[SourceProviderType] = SourceProviderType.ORG
    board: ClassVar[SourceBoard] = SourceBoard.FINANCE
    country: ClassVar[GeoCountry] = GeoCountry.CN
    fetch_type: ClassVar[SourceFetchType] = SourceFetchType.AUTOMATIC
    _datasets_module: ClassVar[str] = f"{_DATASETS_PKG}.ok"

    @classmethod
    def from_setting(cls, setting) -> FakeSource:
        raise NotImplementedError

    def dataset(self, name: str) -> BaseDataset:
        _klass = self.get_dataset_class(name)
        if not _klass:
            raise ValueError(f"Dataset '{name}' not found.")
        return _klass(
            asset=self.vault.asset(rel=_klass.name, filekind=_klass.filekind, partitions=_klass.partitions),
            database=self.store.database(_klass.name),
            log_stream=self.log_stream,
            tags=self.tags,
            _authorized=True,
        )


class FakeAbstractSource(FakeSource):
    _datasets_module: ClassVar[str] = f"{_DATASETS_PKG}.abstract"
