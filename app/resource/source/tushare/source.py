from __future__ import annotations

from typing import ClassVar

from pydantic import Field, PrivateAttr, model_validator

from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import (
    SourceFetchType,
    SourceProvider,
    SourceProviderType,
)
from app.resource.asset._common._asset import BaseAsset
from app.resource.source._common._source import BaseSource
from app.resource.source.tushare.dataset import TushareDataset
from app.resource.source.tushare.session import TushareSession
from app.resource.store._common._database import BaseDatabase
from app.setting._source import TushareSourceSetting


class TushareSource(BaseSource):
    """
    Tushare data source for CN trading and financial markets

    Attributes:
    ----------
        frn (str):
            Source FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.TUSHARE
        type (SourceProviderType):
            Source provider type, fixed to SourceProviderType.ORG
        board (SourceBoard):
            Source board, fixed to SourceBoard.FINANCE
        country (GeoCountry):
            Source country, fixed to GeoCountry.CN
        name (str):
            Source name, e.g. "prod_tushare"
        description (str):
            Source description, default is "Tushare CN trading and financial data source."
        provision_path (str):
            Path for provisioning the source, e.g. "local/provision/source/tushare/"
        vault (BaseVault | AbstractVaultSetting | str):
            Source landing vault, resolved through GlobalVaults
        store (BaseStore | AbstractStoreSetting | str):
            Source semi-structured data store, resolved through GlobalStores
        log_stream (LogStream | LogSetting | str | None):
            Source log stream, resolved through GlobalLogStreams,
            a stream named after the source is used when omitted
        key (str):
            Tushare API token
        ttl_hours (float):
            Tushare session time-to-live in hours, default is 0.5
        tags (dict[str, str]):
            Source tags

    Methods:
    ----------
        from_setting(setting: TushareSourceSetting) -> TushareSource:
            Build the source from its setting.
        dataset(name: str) -> TushareDataset:
            Construct a dataset by name with the source session, vault, store and log stream.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.TUSHARE
    type: ClassVar[SourceProviderType] = SourceProviderType.ORG
    board: ClassVar[SourceBoard] = SourceBoard.FINANCE
    country: ClassVar[GeoCountry] = GeoCountry.CN
    fetch_type: ClassVar[SourceFetchType] = SourceFetchType.AUTOMATIC

    # Enforced private class variables
    # [Inherited] _provision_path: ClassVar[str]
    _datasets_module: ClassVar[str] = "app.resource.source.tushare.datasets"

    # Enforced public instance variables
    # [Inherited] name: str
    # [Inherited] vault: BaseVault
    # [Inherited] store: BaseStore
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]
    key: str = Field(
        ...,
        description="[Required] API key.",
        min_length=1,
    )
    description: str = Field(
        default="Tushare CN trading and financial data source.",
        description="[Optional] Source description.",
    )
    ttl_hours: float = Field(
        default=0.5,
        description="[Optional] TTL for Tushare session in hours.",
        gt=0,
    )

    # Private instance variables
    # [Inherited] _dataset_classes: list[type[BaseDataset]] | None
    # [Inherited] _datasets: list[BaseDataset] | None
    # [Inherited] _lock: threading.RLock
    _session: TushareSession | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _derive_session(self) -> "TushareSource":
        if self._session is None:
            self._session = TushareSession(
                key=self.key,
                ttl_hours=self.ttl_hours,
            )
        return self

    @classmethod
    def from_setting(
        cls,
        setting: TushareSourceSetting,
    ) -> TushareSource:
        return cls(
            name=setting.name,
            key=setting.key,
            ttl_hours=setting.session_ttl_hours,
            description=setting.description,
            vault=setting.vault,
            store=setting.store,
            log_stream=setting.log,
            tags=setting.tags,
        )

    def dataset(
        self,
        name: str,
    ) -> TushareDataset:
        _klass: type[TushareDataset] | None = self.get_dataset_class(name)
        if not _klass:
            raise ValueError(f"Dataset '{name}' not found.")
        _klass_name: str = _klass.name
        _asset: BaseAsset = self.vault.asset(
            rel=f"{_klass_name}",
            filekind=_klass.filekind,
            partitions=_klass.partitions,
        )
        _database: BaseDatabase = self.store.database(f"{_klass_name}")
        _instance: TushareDataset = _klass(
            session=self._session,
            asset=_asset,
            database=_database,
            log_stream=self.log_stream,
            tags=self.tags,
            _authorized=True,
        )
        return _instance
