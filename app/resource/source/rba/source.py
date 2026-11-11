from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import (
    SourceFetchType,
    SourceProvider,
    SourceProviderType,
)
from app.resource.asset._common._asset import BaseAsset
from app.resource.source._common._source import BaseSource
from app.resource.source.rba.dataset import RBADataset
from app.resource.store._common._database import BaseDatabase
from app.setting._source import RBASourceSetting


class RBASource(BaseSource):
    """
    RBA (Reserve Bank of Australia) data source for AU financial data

    Tables are pulled through the third party `rbadata` package, no key is needed.

    URL: https://www.rba.gov.au/statistics/

    Attributes:
    ----------
        frn (str):
            Source FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.RBA
        type (SourceProviderType):
            Source provider type, fixed to SourceProviderType.GOV
        board (SourceBoard):
            Source board, fixed to SourceBoard.FINANCE
        country (GeoCountry):
            Source country, fixed to GeoCountry.AU
        fetch_type (SourceFetchType):
            Source fetch type, fixed to SourceFetchType.AUTOMATIC
        name (str):
            Source name, e.g. "prod_rba"
        description (str):
            Source description, default is "RBA AU financial data source."
        timezone (str):
            IANA timezone of the source, default is "UTC"
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
        from_setting(setting: RBASourceSetting) -> RBASource:
            Build the source from its setting.
        dataset(name: str) -> RBADataset:
            Construct a dataset by name with the source vault, store and log stream.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.RBA
    type: ClassVar[SourceProviderType] = SourceProviderType.GOV
    board: ClassVar[SourceBoard] = SourceBoard.FINANCE
    country: ClassVar[GeoCountry] = GeoCountry.AU
    fetch_type: ClassVar[SourceFetchType] = SourceFetchType.AUTOMATIC

    # Enforced private class variables
    _datasets_module: ClassVar[str] = "app.resource.source.rba.datasets"

    # Enforced public instance variables
    # [Inherited] name: str
    # [Inherited] vault: BaseVault
    # [Inherited] store: BaseStore
    # [Inherited] log_stream: LogStream
    # [Inherited] max_threads: int
    # [Inherited] provision_path: Path | str | None
    # [Inherited] timezone: str
    # [Inherited] tags: dict[str, str]
    description: str = Field(
        default="RBA AU financial data source.",
        description="[Optional] Source description.",
    )

    # Private instance variables
    # [Inherited] _dataset_classes: list[type[BaseDataset]] | None
    # [Inherited] _datasets: list[BaseDataset] | None
    # [Inherited] _lock: threading.RLock

    @classmethod
    def from_setting(
        cls,
        setting: RBASourceSetting,
    ) -> RBASource:
        return cls(
            name=setting.name,
            description=setting.description,
            timezone=setting.timezone,
            max_threads=setting.max_threads,
            vault=setting.vault,
            store=setting.store,
            log_stream=setting.log,
            tags=setting.tags,
        )

    def dataset(
        self,
        name: str,
    ) -> RBADataset:
        _klass: type[RBADataset] | None = self.get_dataset_class(name)
        if not _klass:
            raise ValueError(f"Dataset '{name}' not found.")
        _klass_name: str = _klass.name
        _asset: BaseAsset = self.vault.asset(
            rel=f"{_klass_name}",
            filekind=_klass.filekind,
            partitions=_klass.partitions,
        )
        _database: BaseDatabase = self.store.database(f"{_klass_name}")
        _instance: RBADataset = _klass(
            timezone=self.timezone,
            asset=_asset,
            database=_database,
            log_stream=self.log_stream,
            tags=self.tags,
            _authorized=True,
        )
        return _instance
