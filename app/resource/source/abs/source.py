from __future__ import annotations

from typing import ClassVar

from pydantic import Field, PrivateAttr

from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import (
    SourceFetchType,
    SourceProvider,
    SourceProviderType,
)
from app.resource._client.web.client import WebClient
from app.resource.asset._common._asset import BaseAsset
from app.resource.source._common._source import BaseSource
from app.resource.source.abs.dataset import ABSDataset
from app.resource.store._common._database import BaseDatabase
from app.setting._source import ABSSourceSetting


class ABSSource(BaseSource):
    """
    ABS (Australian Bureau of Statistics) data source for AU macro statistics

    The ABS SDMX REST API is public, no key is needed.

    URL: https://data.api.abs.gov.au

    Attributes:
    ----------
        frn (str):
            Source FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.ABS
        type (SourceProviderType):
            Source provider type, fixed to SourceProviderType.GOV
        board (SourceBoard):
            Source board, fixed to SourceBoard.MACRO
        country (GeoCountry):
            Source country, fixed to GeoCountry.AU
        fetch_type (SourceFetchType):
            Source fetch type, fixed to SourceFetchType.AUTOMATIC
        name (str):
            Source name, e.g. "prod_abs"
        description (str):
            Source description, default is "ABS AU macro statistics data source."
        timeout_seconds (float):
            Timeout of a single API request in seconds, default is 60
        vault (BaseVault | AbstractVaultSetting | str):
            Source landing vault, resolved through GlobalVaults
        store (BaseStore | AbstractStoreSetting | str):
            Source semi-structured data store, resolved through GlobalStores
        log_stream (LogStream | LogSetting | str | None):
            Source log stream, resolved through GlobalLogStreams,
            a stream named after the source is used when omitted
        tags (dict[str, str]):
            Source tags

    Methods:
    ----------
        from_setting(setting: ABSSourceSetting) -> ABSSource:
            Build the source from its setting.
        dataset(name: str) -> ABSDataset:
            Construct a dataset by name with the source client, vault, store and log stream.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.ABS
    type: ClassVar[SourceProviderType] = SourceProviderType.GOV
    board: ClassVar[SourceBoard] = SourceBoard.MACRO
    country: ClassVar[GeoCountry] = GeoCountry.AU
    fetch_type: ClassVar[SourceFetchType] = SourceFetchType.AUTOMATIC

    # Enforced private class variables
    _datasets_module: ClassVar[str] = "app.resource.source.abs.datasets"

    # Enforced public instance variables
    # [Inherited] name: str
    # [Inherited] vault: BaseVault
    # [Inherited] store: BaseStore
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]
    description: str = Field(
        default="ABS AU macro statistics data source.",
        description="[Optional] Source description.",
    )
    timeout_seconds: float = Field(
        default=60,
        description="[Optional] Timeout of a single API request in seconds.",
        gt=0,
    )

    # Private instance variables
    # [Inherited] _dataset_classes: list[type[BaseDataset]] | None
    # [Inherited] _datasets: list[BaseDataset] | None
    # [Inherited] _lock: threading.RLock
    _client: WebClient = PrivateAttr(default_factory=WebClient)

    @classmethod
    def from_setting(
        cls,
        setting: ABSSourceSetting,
    ) -> ABSSource:
        return cls(
            name=setting.name,
            description=setting.description,
            timeout_seconds=setting.timeout_seconds,
            max_threads=setting.max_threads,
            vault=setting.vault,
            store=setting.store,
            log_stream=setting.log,
            tags=setting.tags,
        )

    def dataset(
        self,
        name: str,
    ) -> ABSDataset:
        _klass: type[ABSDataset] | None = self.get_dataset_class(name)
        if not _klass:
            raise ValueError(f"Dataset '{name}' not found.")
        _klass_name: str = _klass.name
        _asset: BaseAsset = self.vault.asset(
            rel=f"{_klass_name}",
            filekind=_klass.filekind,
            partitions=_klass.partitions,
        )
        _database: BaseDatabase = self.store.database(f"{_klass_name}")
        _instance: ABSDataset = _klass(
            client=self._client,
            timeout_seconds=self.timeout_seconds,
            asset=_asset,
            database=_database,
            log_stream=self.log_stream,
            tags=self.tags,
            _authorized=True,
        )
        return _instance
