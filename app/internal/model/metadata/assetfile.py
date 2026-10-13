from __future__ import annotations

import polars as pl
from pydantic import Field

from app.internal.abstract.domain import IAbstractDomain
from app.internal.model.definition import DataframeDefinition
from app.internal.model.quality import DataframeQuality


class AssetfileMetadata(IAbstractDomain):
    """
    Assetfile metadata containing both the quality and definition of a dataframe.

    Args:
    ----------
        quality (DataframeQuality):
            Quality of the dataframe
        definition (DataframeDefinition):
            Definition of the dataframe

    Methods
    ----------
        from_frame(cls, df: pl.DataFrame) -> "AssetfileMetadata":
            Creates an AssetfileMetadata instance from a Polars DataFrame.

    """

    quality: DataframeQuality = Field(
        ...,
        description="[Required] Quality of the dataframe",
    )
    definition: DataframeDefinition = Field(
        ...,
        description="[Required] Definition of the dataframe",
    )

    @classmethod
    def from_frame(
        cls,
        df: pl.DataFrame,
    ) -> "AssetfileMetadata":
        return cls(
            quality=DataframeQuality.from_frame(df),
            definition=DataframeDefinition.from_frame(df),
        )
