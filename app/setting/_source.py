from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.internal.abstract.setting import IAbstractTaggedSetting
from app.internal.constant.geocountry import GeoCountry
from app.internal.constant.sourceboard import SourceBoard
from app.internal.constant.sourceprovider import SourceProvider, SourceProviderType
from app.setting._log import LogSetting


class AbstractSourceSetting(IAbstractTaggedSetting):
    """
    Abstract data source setting

    Attributes:
        name (str): The name of the data source.
        provider (SourceProvider): The data provider for the source.
        type (SourceProviderType): The type of the data provider for the source.
        board (SourceBoard): The data board for the source.
        country (GeoCountry): The geographic country for the data source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        tags (dict[str, str]): The tags associated with the data source.

    """

    name: str = Field(
        ...,
        description="[Required] The name of the data source.",
    )
    provider: SourceProvider = Field(
        ...,
        description="[discriminator] The data provider for the source.",
    )
    type: SourceProviderType = Field(
        ...,
        description="[Required] The type of the data provider for the source.",
    )
    board: SourceBoard = Field(
        ...,
        description="[Required] The data board for the source.",
    )
    country: GeoCountry = Field(
        ...,
        description="[Required] The geographic country for the data source.",
    )
    description: str = Field(
        default="",
        description="[Optional] The description of the data source.",
    )
    log: LogSetting | None = Field(
        default=None,
        description="[Optional] The log configuration for the data source.",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] The tags associated with the data source.",
    )

    @property
    def frn(self) -> str:
        return f"setting:source:provider={self.provider}:name={self.name}"

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "name": self.name,
            "board": self.board,
            "type": self.type,
            "country": self.country,
        }


class ABSSourceSetting(AbstractSourceSetting):
    """
    ABS (Australia government) data source setting.

    Attributes:
        name (str): The name of the data source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        tags (dict[str, str]): The tags associated with the data source.

    """

    # Inherited from AbstractSourceSetting
    # -- name: str
    # -- description: str
    # -- log: LogSetting | None
    # -- tags: dict[str, str]
    provider: Literal[SourceProvider.ABS] = SourceProvider.ABS
    type: Literal[SourceProviderType.GOV] = SourceProviderType.GOV
    board: Literal[SourceBoard.MACRO] = SourceBoard.MACRO
    country: Literal[GeoCountry.AU] = GeoCountry.AU


class TushareSourceSetting(AbstractSourceSetting):
    """
    Tushare (China 3rd-party organization) data source setting.

    Attributes:
        name (str): The name of the data source.
        description (str): The description of the data source.
        log (LogSetting | None): The log configuration for the data source.
        key (str): The API key for accessing the Tushare data source.
        tags (dict[str, str]): The tags associated with the data source.

    """

    # Inherited from AbstractSourceSetting
    # -- name: str
    # -- description: str
    # -- log: LogSetting | None
    # -- tags: dict[str, str]
    provider: Literal[SourceProvider.TUSHARE] = SourceProvider.TUSHARE
    type: Literal[SourceProviderType.ORG] = SourceProviderType.ORG
    board: Literal[SourceBoard.FINANCE] = SourceBoard.FINANCE
    country: Literal[GeoCountry.CN] = GeoCountry.CN
    key: str = Field(
        ...,
        description="[Required] The API key for accessing Tushare data source.",
    )


UnionSourceSetting = Annotated[
    Union[
        ABSSourceSetting,
        TushareSourceSetting,
    ],
    Field(discriminator="provider"),
]
