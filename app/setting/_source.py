from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.sourceprovider import SourceProvider
from app.internal.util.frn import IFrn
from app.setting._log import LogSetting
from app.setting._store import UnionStoreSetting
from app.setting._vault import UnionVaultSetting

SOURCE_NAME_PATTERN: str = r"^[A-Za-z0-9_]+$"


class AbstractSourceSetting(IAbstractTaggedSetting):
    """
    Abstract data source setting

    Attributes:
    ----------
        name (str): The name of the data source.
        provider (SourceProvider): The data provider for the source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        vault (UnionVaultSetting | str): The vault configuration or name.
        store (UnionStoreSetting | str): The store configuration or name.
        tags (dict[str, str]): The tags associated with the data source.

    """

    name: str = Field(
        ...,
        description="[Required] The name of the data source.",
        pattern=SOURCE_NAME_PATTERN,
    )
    provider: SourceProvider = Field(
        ...,
        description="[discriminator] The data provider for the source.",
    )
    description: str = Field(
        default="",
        description="[Optional] The description of the data source.",
    )
    log: LogSetting | None = Field(
        default=None,
        description="[Optional] The log configuration for the data source.",
    )
    vault: UnionVaultSetting | str | None = Field(
        default=None,
        description="[Optional] The vault configuration for the data source.",
    )
    store: UnionStoreSetting | str | None = Field(
        default=None,
        description="[Optional] The store configuration for the data source.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] The tags associated with the data source.",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "setting",
                "source",
                f"provider={self.provider}",
                f"name={self.name}",
            ]
        )

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "name": self.name,
        }


class ABSSourceSetting(AbstractSourceSetting):
    """
    ABS (Australia government) data source setting.

    Attributes:
    ----------
        name (str): The name of the data source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        vault (UnionVaultSetting | str): The vault configuration or name.
        store (UnionStoreSetting | str): The store configuration or name.
        tags (dict[str, str]): The tags associated with the data source.

    """

    # Inherited from AbstractSourceSetting
    # -- name: str
    # -- description: str
    # -- log: LogSetting | None
    # -- tags: dict[str, str]
    provider: Literal[SourceProvider.ABS] = SourceProvider.ABS


class NSWVGSourceSetting(AbstractSourceSetting):
    """
    New South Wales Valuer General (NSW VG) data source setting.

    Attributes:
    ----------
        name (str): The name of the data source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        vault (UnionVaultSetting | str): The vault configuration or name.
        store (UnionStoreSetting | str): The store configuration or name.
        tags (dict[str, str]): The tags associated with the data source.

    """

    # Inherited from AbstractSourceSetting
    # -- name: str
    # -- description: str
    # -- log: LogSetting | None
    # -- tags: dict[str, str]
    provider: Literal[SourceProvider.NSW_VG] = SourceProvider.NSW_VG


class TushareSourceSetting(AbstractSourceSetting):
    """
    Tushare (China 3rd-party organization) data source setting.

    Attributes:
    ----------
        name (str): The name of the data source.
        description (str): The description of the data source.
        key (str): The API key for accessing the Tushare data source.
        session_ttl_hours (float): The Tushare session TTL in hours (> 0).
        log (LogSetting | None): The log configuration for the data source.
        vault (UnionVaultSetting | str): The vault configuration or name.
        store (UnionStoreSetting | str): The store configuration or name.
        tags (dict[str, str]): The tags associated with the data source.

    """

    # Inherited from AbstractSourceSetting
    # -- name: str
    # -- description: str
    # -- log: LogSetting | None
    # -- tags: dict[str, str]
    provider: Literal[SourceProvider.TUSHARE] = SourceProvider.TUSHARE
    key: str = Field(
        ...,
        description="[Required] The API key for accessing Tushare data source.",
    )
    session_ttl_hours: float = Field(
        default=0.5,
        description="[Optional] The time-to-live (TTL) for the Tushare session in hours.",
        gt=0,
    )


UnionSourceSetting = Annotated[
    Union[
        ABSSourceSetting,
        NSWVGSourceSetting,
        TushareSourceSetting,
    ],
    Field(discriminator="provider"),
]
