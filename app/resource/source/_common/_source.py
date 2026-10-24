from __future__ import annotations

import importlib
import inspect
import pkgutil
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr, model_validator

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import (
    SourceFetchType,
    SourceProvider,
    SourceProviderType,
)
from app.internal.logstream import LogStream
from app.internal.util.frn import IFrn
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.stores import GlobalStores
from app.resource._global.vaults import GlobalVaults
from app.resource.asset._common._vault import BaseVault
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common._dataset import BaseDataset
from app.resource.store._common._store import BaseStore
from app.resource.store.file.store import FileStore
from app.setting._log import LogSetting
from app.setting._source import UnionSourceSetting
from app.setting._store import AbstractStoreSetting
from app.setting._vault import AbstractVaultSetting


class BaseSource(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for data sources, each source owns a collection of datasets

    Attributes:
    ----------
        frn (str):
            Source FRN (Fortress resource identifier)

    Args:
    ----------
        provider (SourceProvider):
            Source provider, declared by the subclass
        type (SourceProviderType):
            Source provider type, declared by the subclass
        board (SourceBoard):
            Source board, declared by the subclass
        country (GeoCountry):
            Source country, declared by the subclass
        name (str):
            Source name
        description (str | None):
            Source description
        max_threads (int):
            Datasets of the source a node runs at the same time, default is 1
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
        list_dataset_classes() -> list[type[BaseDataset]]:
            Discover dataset classes under the subclass `_datasets_module`,
            raising TypeError if any of them is abstract.
        from_setting(setting: UnionSourceSetting) -> BaseSource:
            Build the source from its setting.
        list_dataset_names() -> list[str]:
            List the names of all discovered datasets.
        get_dataset_class(name: str) -> type[BaseDataset] | None:
            Get a discovered dataset class by name, None if not found.
        dataset(name: str) -> BaseDataset:
            Construct a dataset by name with the source vault, store and log stream.
        list_datasets() -> list[BaseDataset]:
            Construct (lazily, then cached) all datasets of the source.
        show() -> None:
            Log the source and its dataset names.
        export() -> dict[str, Any]:
            Export the source as a dictionary.

    """

    # --------------------------------------------------
    # Class variables section
    # --------------------------------------------------

    # ---------- Enforced PUBLIC class variables ----------
    provider: ClassVar[SourceProvider]
    type: ClassVar[SourceProviderType]
    board: ClassVar[SourceBoard]
    country: ClassVar[GeoCountry]
    fetch_type: ClassVar[SourceFetchType]

    # ---------- Enforced PRIVATE class variables ----------
    _datasets_module: ClassVar[str]
    _provision_base_path: ClassVar[Path] = Path("./local/provision/source")

    # --------------------------------------------------
    # Instance variables section
    # --------------------------------------------------

    # ---------- Enforced PUBLIC instance variables ----------
    name: str = Field(
        ...,
        description="[Required] Source name",
    )
    description: str | None = Field(
        default=None,
        description="[Optional] Source description.",
    )
    max_threads: int = Field(
        default=1,
        ge=1,
        description="[Optional] Datasets of the source run at the same time",
    )
    provision_path: Path | str | None = Field(
        default=None,
        description="[Optional] The provision path for manual downloads.",
    )
    vault: BaseVault | AbstractVaultSetting | str | None = Field(
        default=None,
        description="[Optional] Source landing vault",
    )
    store: BaseStore | AbstractStoreSetting | str | None = Field(
        default=None,
        description="[Optional] Source semi-structured data store",
    )
    log_stream: LogStream | LogSetting | str | None = Field(
        default=None,
        description="[Optional] Source log stream",
    )
    # [Inherited] tags: dict[str, str]

    # ---------- Enforced PRIVATE instance variables ----------
    _dataset_classes: list[type[BaseDataset]] | None = PrivateAttr(default=None)
    _datasets: list[BaseDataset] | None = PrivateAttr(default=None)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_provision_path(self) -> "BaseSource":
        if self.provision_path is None:
            _path: Path = self._provision_base_path / self.name
        else:
            _path: Path = Path(self.provision_path)
        _path: Path = Path(_path).expanduser().resolve()
        object.__setattr__(self, "provision_path", Path(_path))
        return self

    @model_validator(mode="after")
    def _derive_vault(self) -> "BaseSource":
        _vault: BaseVault = GlobalVaults.resolve(
            value=self.vault,
            default=LocalVault.default(name="source"),
        )
        object.__setattr__(self, "vault", _vault)
        return self

    @model_validator(mode="after")
    def _derive_store(self) -> "BaseSource":
        _store: BaseStore = GlobalStores.resolve(
            value=self.store,
            default=FileStore.default(name="source"),
        )
        object.__setattr__(self, "store", _store)
        return self

    @model_validator(mode="after")
    def _derive_log_stream(self) -> "BaseSource":
        _log_stream: LogStream = GlobalLogStreams.resolve(
            value=self.log_stream,
            default=LogStream(name=f"{self.name}"),
        )
        object.__setattr__(self, "log_stream", _log_stream)
        return self

    @model_validator(mode="after")
    def _derive_dataset_classes(self) -> "BaseSource":
        self._dataset_classes = self.list_dataset_classes()
        return self

    @classmethod
    def list_dataset_classes(cls) -> list[type[BaseDataset]]:
        _package: ModuleType = importlib.import_module(cls._datasets_module)
        _result: list[type[BaseDataset]] = []
        _module_infos = pkgutil.iter_modules(
            path=_package.__path__,
            prefix=f"{_package.__name__}.",
        )
        for _module_info in _module_infos:
            _module = importlib.import_module(_module_info.name)
            for _, _member in inspect.getmembers(_module, inspect.isclass):
                if _member.__module__ != _module.__name__:
                    continue
                if not issubclass(_member, BaseDataset) or _member is BaseDataset:
                    continue
                if inspect.isabstract(_member):
                    # Raise if the dataset class is abstract
                    raise TypeError(
                        f"{_member.__module__}.{_member.__name__} is abstract, "
                        f"unimplemented: {sorted(_member.__abstractmethods__)}"
                    )
                _result.append(_member)
        return _result

    @classmethod
    @abstractmethod
    def from_setting(
        cls,
        setting: UnionSourceSetting,
    ) -> BaseSource: ...

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "source",
                f"provider={self.provider}",
                f"name={self.name}",
            ]
        )

    def list_dataset_names(self) -> list[str]:
        res: list[str] = []
        for _klass in self._dataset_classes:
            res.append(_klass.name)
        return res

    def get_dataset_class(
        self,
        name: str,
    ) -> type[BaseDataset] | None:
        for dataset_class in self._dataset_classes:
            if dataset_class.name == name:
                return dataset_class
        return None

    @abstractmethod
    def dataset(
        self,
        name: str,
    ) -> BaseDataset: ...

    def list_datasets(self) -> list[BaseDataset]:
        with self._lock:
            _result: list[BaseDataset] = []
            if self._datasets is None:
                for _klass in self._dataset_classes:
                    _klass_name: str = _klass.name
                    _instance: BaseDataset = self.dataset(name=_klass_name)
                    _result.append(_instance)
                self._datasets = _result
            return list(self._datasets)

    def show(self) -> None:
        self.log_stream.info(f"Source {self.provider} {self.name}")
        for dataset_name in self.list_dataset_names():
            self.log_stream.info(f" - Dataset {dataset_name}")

    def export(self) -> dict[str, Any]:
        _res: dict[str, Any] = self.model_dump(
            exclude={"vault", "store", "log_stream"},
            mode="json",
            round_trip=True,
        )
        # ClassVars are not part of model_dump, so add the identity explicitly
        _res["frn"] = self.frn
        _res["provider"] = str(self.provider)
        _res["type"] = str(self.type)
        _res["board"] = str(self.board)
        _res["country"] = str(self.country)
        _res["fetch_type"] = str(self.fetch_type)
        _res["vault"] = self.vault.export()
        _res["store"] = self.store.export()
        return _res
