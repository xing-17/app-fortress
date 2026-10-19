from __future__ import annotations

from pathlib import Path
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
from app.resource.source.nswvg.dataset import NSWVGDataset
from app.resource.store._common._database import BaseDatabase
from app.setting._source import NSWVGSourceSetting


class NSWVGSource(BaseSource):
    """
    NSW Valuer General data source for AU property sales information (PSI)

    The files are downloaded manually and dropped into the provision path,
    one sub-directory per dataset.

    Attributes:
    ----------
        frn (str):
            Source FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, fixed to SourceProvider.NSWVG
        type (SourceProviderType):
            Source provider type, fixed to SourceProviderType.ORG
        board (SourceBoard):
            Source board, fixed to SourceBoard.HOUSING
        country (GeoCountry):
            Source country, fixed to GeoCountry.AU
        fetch_type (SourceFetchType):
            Source fetch type, fixed to SourceFetchType.PROVISION
        name (str):
            Source name, e.g. "prod_nswvg"
        description (str):
            Source description, default is "NSW Valuer General data source for properties."
        provision_path (Path | str | None):
            Path holding the manually downloaded files, e.g. "local/provision/source/nswvg/"
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
        from_setting(setting: NSWVGSourceSetting) -> NSWVGSource:
            Build the source from its setting.
        dataset(name: str) -> NSWVGDataset:
            Construct a dataset by name with its provision directory, asset and database.

    """

    # Enforced public class variables
    provider: ClassVar[SourceProvider] = SourceProvider.NSWVG
    type: ClassVar[SourceProviderType] = SourceProviderType.ORG
    board: ClassVar[SourceBoard] = SourceBoard.HOUSING
    country: ClassVar[GeoCountry] = GeoCountry.AU
    fetch_type: ClassVar[SourceFetchType] = SourceFetchType.PROVISION

    # Enforced private class variables
    _datasets_module: ClassVar[str] = "app.resource.source.nswvg.datasets"

    # Enforced public instance variables
    # [Inherited] name: str
    # [Inherited] vault: BaseVault
    # [Inherited] store: BaseStore
    # [Inherited] log_stream: LogStream
    # [Inherited] tags: dict[str, str]
    description: str = Field(
        default="NSW Valuer General data source for properties.",
        description="[Optional] Source description.",
    )

    # Private instance variables
    # [Inherited] _dataset_classes: list[type[BaseDataset]] | None
    # [Inherited] _datasets: list[BaseDataset] | None
    # [Inherited] _lock: threading.RLock

    @classmethod
    def from_setting(
        cls,
        setting: NSWVGSourceSetting,
    ) -> NSWVGSource:
        return cls(
            name=setting.name,
            provision_path=setting.provision_path,
            description=setting.description,
            vault=setting.vault,
            store=setting.store,
            log_stream=setting.log,
            tags=setting.tags,
        )

    def dataset(
        self,
        name: str,
    ) -> NSWVGDataset:
        _klass: type[NSWVGDataset] | None = self.get_dataset_class(name)
        if not _klass:
            raise ValueError(f"Dataset '{name}' not found.")
        _klass_name: str = _klass.name
        _asset: BaseAsset = self.vault.asset(
            rel=f"{_klass_name}",
            filekind=_klass.filekind,
            partitions=_klass.partitions,
        )
        _database: BaseDatabase = self.store.database(f"{_klass_name}")
        _provision_path: Path = self.provision_path / f"{_klass_name}"
        _instance: NSWVGDataset = _klass(
            provision_path=_provision_path,
            asset=_asset,
            database=_database,
            log_stream=self.log_stream,
            tags=self.tags,
            _authorized=True,
        )
        return _instance
